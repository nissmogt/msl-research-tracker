from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import json
import os
from datetime import datetime
# Removed lru_cache import - using smart_cache instead

from database import get_db, engine
from models import Base
from schemas import (
    ArticleResponse, SearchRequest,
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse,
    InsightRequest,
    FetchPubmedRequest,
    ReliabilityRequest, ReliabilityResponse
)
from services import (
    ArticleService, ConversationService, AIService
)
from pubmed_service import PubMedService
from reliability_meter import ReliabilityMeter, UseCase as ReliabilityUseCase
from middleware.auth_edge import EdgeAuthMiddleware
# Add reliability router
from routers import reliability as reliability_router
# Rate limiting imports - Re-enabled with Redis backend for production
try:
    from middleware.rate_limit import RateLimitingMiddleware, limiter, search_rate_limit, pubmed_search_rate_limit, ai_insights_rate_limit
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    RATE_LIMITING_ENABLED = True
except ImportError as e:
    print(f"⚠️ Rate limiting disabled: {e}")
    RATE_LIMITING_ENABLED = False

# Create database tables
Base.metadata.create_all(bind=engine)

# Ensure insights column exists (for backwards compatibility)
try:
    from check_db_schema import ensure_insights_column
    ensure_insights_column()
except Exception as e:
    print(f"Note: Could not check/add insights column: {e}")

# Initialize journal data on startup
try:
    from journal_service import JournalImpactFactorService
    from database import SessionLocal
    
    # Check if journals table is empty and populate if needed
    db = SessionLocal()
    from models import Journal
    journal_count = db.query(Journal).count()
    
    if journal_count == 0:
        print("📚 Initializing journal impact factor database...")
        journal_service = JournalImpactFactorService()
        journal_service.populate_initial_data(db)
    else:
        print(f"📚 Journal database already contains {journal_count} journals")
    
    db.close()
except Exception as e:
    print(f"⚠️  Warning: Could not initialize journal data: {e}")

app = FastAPI(
    title="MSL Research Tracker API",
    description="Medical Science Liaison Research Tracking and Insights Platform",
    version="1.0.0"
)

# Add rate limiting to the app - temporarily disabled due to slowapi dependency issue
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add Rate Limiting middleware (before auth middleware) - temporarily disabled
# app.add_middleware(RateLimitingMiddleware)

# Add Edge Authentication middleware to validate X-Edge-Auth header
print("🔐 Registering EdgeAuthMiddleware...")
print(f"🔍 EDGE_SECRET configured: {bool(os.getenv('EDGE_SECRET'))}")
print(f"🔍 EDGE_SECRET length: {len(os.getenv('EDGE_SECRET', ''))}")
try:
    app.add_middleware(EdgeAuthMiddleware)
    print("✅ EdgeAuthMiddleware registered successfully")
except Exception as e:
    print(f"❌ Error registering EdgeAuthMiddleware: {e}")
    # For debugging - still register middleware even if there are issues
    app.add_middleware(EdgeAuthMiddleware)

# Rate limiting middleware - only add if successfully imported
if RATE_LIMITING_ENABLED:
    print("✅ Rate limiting enabled with Redis backend")
    app.add_middleware(RateLimitingMiddleware)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
else:
    print("⚠️ Rate limiting DISABLED - add Redis to enable protection")

# CORS middleware for React frontend - now restricted to insightmsl.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://insightmsl.com",
        "https://www.insightmsl.com"
        # Remove localhost origins in production - use environment-specific config
    ] if os.getenv("ENVIRONMENT") == "production" else [
        "https://insightmsl.com", 
        "https://www.insightmsl.com",
        "http://localhost:3000",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-Edge-Auth"  # Allow our edge auth header
    ],
)

# Mount reliability router for snapshot-based scoring
app.include_router(reliability_router.router)

@app.get("/")
async def root():
    """Root endpoint for Railway health checks"""
    return {"status": "MSL Research Tracker API is running", "version": "1.0.1"}



@app.get("/health")
async def health_check():
    """
    Secure health check endpoint - only returns essential status information.
    Does not expose configuration details for security reasons.
    """
    try:
        # Test database connection
        db = next(get_db())
        from sqlalchemy import text
        result = db.execute(text("SELECT 1")).fetchone()
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
            "service": "MSL Research Tracker API"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "database": "disconnected",
            "timestamp": datetime.now().isoformat(),
            "service": "MSL Research Tracker API"
        }

@app.get("/healthz")
async def kubernetes_health():
    """Kubernetes-style liveness probe"""
    return {"status": "ok", "checks": {"database": "pass"}}

@app.get("/readyz")
async def kubernetes_readiness():
    """Kubernetes-style readiness probe with dependency checks"""
    try:
        # Check database connectivity
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        
        # Check OpenAI API key presence (don't test actual API)
        from config import settings
        openai_ready = bool(settings.OPENAI_API_KEY)
        
        return {
            "status": "ready",
            "checks": {
                "database": "pass",
                "openai_config": "pass" if openai_ready else "warn"
            }
        }
    except Exception as e:
        print(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

# Smart caching strategy for medical literature
from functools import wraps
import time

def get_cache_duration(days_back: int) -> int:
    """
    Determine cache duration based on search recency
    Fresh medical research needs shorter cache times
    """
    if days_back <= 1:      # Last 24 hours - no cache (always fresh)
        return 0            
    elif days_back <= 7:    # Last week - short cache
        return 300          # Cache 5 minutes
    elif days_back <= 30:   # Last month - medium cache
        return 900          # Cache 15 minutes
    else:                   # Older searches - longer cache
        return 1800         # Cache 30 minutes

def smart_cache():
    """Time-aware cache decorator for medical literature searches"""
    def decorator(func):
        cache = {}
        cache_time = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract days_back from args (therapeutic_area, days_back)
            days_back = args[1] if len(args) > 1 else kwargs.get('days_back', 7)
            cache_duration = get_cache_duration(days_back)
            
            # No caching for 24-hour searches - always fresh
            if cache_duration == 0:
                print(f"🔴 NO CACHE for 24hr search: {args[0]}")
                return func(*args, **kwargs)
            
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()
            
            # Check if we have a cached result and it's still valid
            if key in cache and current_time - cache_time[key] < cache_duration:
                print(f"🟢 Cache HIT for {args[0]} ({days_back}d, {cache_duration}s cache)")
                return cache[key]
            
            # Cache miss or expired - fetch new data
            print(f"🟡 Cache MISS for {args[0]} ({days_back}d) - fetching from PubMed")
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = current_time
            return result
        
        return wrapper
    return decorator

@smart_cache()
def cached_pubmed_search(therapeutic_area: str, days_back: int):
    """Smart cached PubMed search with impact factor sorting"""
    pubmed_service = PubMedService()
    articles = pubmed_service.search_articles(therapeutic_area, days_back)
    
    # Note: Impact factor sorting will be done in the endpoint with DB access
    return articles

def sort_by_impact_factor(articles, db: Session):
    """
    Sort articles by journal impact factor for reliability assessment
    Uses database-driven lookup with intelligent estimation for inclusivity
    """
    from journal_service import JournalImpactFactorService
    
    journal_service = JournalImpactFactorService()
    
    # Add impact factor to each article using the service
    for article in articles:
        journal_name = article.get('journal', '')
        impact_factor, reliability_tier = journal_service.get_impact_factor(journal_name, db)
        
        article['impact_factor'] = impact_factor
        article['reliability_tier'] = reliability_tier
    
    # Sort by impact factor (descending) then by publication date (newest first)
    sorted_articles = sorted(articles, 
                           key=lambda x: (x['impact_factor'], x.get('publication_date', '')), 
                           reverse=True)
    
    print(f"📈 Sorted {len(articles)} articles by impact factor")
    if articles:
        top_journal = sorted_articles[0].get('journal', 'Unknown')
        top_if = sorted_articles[0].get('impact_factor', 0)
        print(f"🏆 Top journal: {top_journal} (IF: {top_if})")
    
    return sorted_articles

def get_reliability_tier(impact_factor):
    """Classify journal reliability based on impact factor"""
    if impact_factor >= 50:
        return 'Tier 1: Highest reliability'
    elif impact_factor >= 10:
        return 'Tier 2: High reliability'  
    elif impact_factor >= 5:
        return 'Tier 3: Good reliability'
    elif impact_factor >= 2:
        return 'Tier 4: Standard reliability'
    else:
        return 'Tier 5: Lower reliability'

# Article search endpoints
# Local database search endpoint temporarily disabled - focusing on PubMed search only
# @app.post("/articles/search", response_model=List[ArticleResponse])
# async def search_articles(...):
#    try:
#        article_service = ArticleService(db)
#        # ... (local search implementation commented out)
#    except Exception as e:
#        # ... (error handling commented out)

# Recent articles endpoint temporarily disabled - focusing on search and insights only
# @app.get("/articles/recent", response_model=List[ArticleResponse])
# async def get_recent_articles(...): ...

@app.post("/articles/search-pubmed")
# @pubmed_search_rate_limit  # Temporarily disabled due to slowapi dependency issue
async def search_pubmed_only(request: SearchRequest, db: Session = Depends(get_db)):
    """Search PubMed with caching and TA-aware reliability scoring"""
    try:
        articles = cached_pubmed_search(request.therapeutic_area, request.days_back)
        print(f"🎯 Processing {len(articles)} articles for use case: {request.use_case}")
        
        # Initialize services outside the loop for efficiency
        reliability_meter = ReliabilityMeter()
        from journal_service import JournalImpactFactorService
        journal_service = JournalImpactFactorService()
        
        response_articles = []
        for article_data in articles:
            # Get impact factor
            impact_factor, _ = journal_service.get_impact_factor(article_data['journal'], db)
            
            # Get TA-aware reliability score
            try:
                use_case_enum = ReliabilityUseCase.CLINICAL if request.use_case.lower() == "clinical" else ReliabilityUseCase.EXPLORATORY
                reliability = reliability_meter.assess_reliability(
                    journal_name=article_data['journal'],
                    therapeutic_area=request.therapeutic_area,
                    use_case=use_case_enum, 
                    db=db,
                    impact_factor=impact_factor
                )
                print(f"✅ Reliability calculated for {article_data['journal']}: {reliability.score}")
            except Exception as e:
                print(f"❌ Error calculating reliability for {article_data['journal']}: {e}")
                import traceback
                traceback.print_exc()
                reliability = None
            
            # Always append article, with or without reliability data
            article_response = {
                "id": None,
                "pubmed_id": article_data['pubmed_id'],
                "title": article_data['title'],
                "authors": article_data['authors'],
                "abstract": article_data['abstract'],
                "publication_date": article_data['publication_date'],
                "journal": article_data['journal'],
                "therapeutic_area": article_data['therapeutic_area'],
                "link": article_data['link'],
                "created_at": None,
                "impact_factor": impact_factor,
            }
            
            if reliability:
                article_response.update({
                    "reliability_tier": reliability.band.value,
                    "reliability_score": reliability.score,
                    "reliability_band": reliability.band.value,
                    "reliability_reasons": reliability.reasons,
                    "uncertainty": reliability.uncertainty
                })
            else:
                # Fallback without reliability data
                article_response.update({
                    "reliability_tier": get_reliability_tier(impact_factor),
                    "reliability_score": None,
                    "reliability_band": None,
                    "reliability_reasons": None,
                    "uncertainty": None
                })
            
            response_articles.append(article_response)
        
        # Sort by reliability score (descending), handling None values
        sorted_articles = sorted(response_articles, key=lambda x: x['reliability_score'] or 0, reverse=True)
        
        return sorted_articles
    except Exception as e:
        print(f"❌ Error in PubMed search with reliability: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PubMed search failed: {str(e)}")

@app.post("/articles/fetch-pubmed")
async def fetch_pubmed_articles(
    request: FetchPubmedRequest,
    db: Session = Depends(get_db)
):
    pubmed_service = PubMedService()
    articles = pubmed_service.search_articles(request.therapeutic_area, request.days_back)
    if articles:
        saved_count = pubmed_service.save_articles_to_db(db, articles)
        return {
            "message": f"Successfully fetched and saved {saved_count} articles",
            "total_found": len(articles),
            "saved_count": saved_count
        }
    else:
        return {
            "message": "No articles found for the specified criteria",
            "total_found": 0,
            "saved_count": 0
        }

@app.get("/therapeutic-areas")
async def get_therapeutic_areas(
    db: Session = Depends(get_db)
):
    from models import TherapeuticArea
    areas = db.query(TherapeuticArea).all()
    return [{"id": area.id, "name": area.name, "description": area.description} for area in areas]

@app.post("/admin/init-journals")
async def initialize_journal_data(
    db: Session = Depends(get_db)
):
    """Initialize journal impact factor database with known high-impact journals"""
    try:
        from journal_service import JournalImpactFactorService
        journal_service = JournalImpactFactorService()
        journal_service.populate_initial_data(db)
        
        return {"message": "Journal impact factor database initialized successfully"}
    except Exception as e:
        return {"error": f"Failed to initialize journal database: {str(e)}"}

# AI Insights endpoints
@app.post("/articles/{pubmed_id}/insights")
# @ai_insights_rate_limit  # Temporarily disabled due to slowapi dependency issue
async def generate_insights(
    pubmed_id: str,
    request: InsightRequest,
    db: Session = Depends(get_db)
):
    ai_service = AIService()
    article_service = ArticleService(db)
    
    # First check if article exists in local database
    article = article_service.get_article_by_pubmed_id(pubmed_id)
    
    if not article:
        # Fetch from PubMed but DON'T save to database
        pubmed_service = PubMedService()
        article_data_list = pubmed_service._batch_fetch_articles([pubmed_id])
        
        if article_data_list and len(article_data_list) > 0:
            # Convert the raw article data to the format expected by AI service
            article_data = article_data_list[0]
            # Create a temporary article-like object for insights generation
            class TempArticle:
                def __init__(self, data):
                    self.pubmed_id = data.get('pubmed_id')
                    self.title = data.get('title')
                    self.abstract = data.get('abstract')
                    self.authors = data.get('authors', [])
                    self.journal = data.get('journal')
                    self.publication_date = data.get('publication_date')
                    self.therapeutic_area = data.get('therapeutic_area')
                    self.link = data.get('link')
                    self.impact_factor = data.get('impact_factor', 1.0)
                    self.reliability_tier = data.get('reliability_tier', 'Unknown')
                    self.use_case = data.get('use_case', 'clinical')
                    # Store the raw data for potential saving
                    self.raw_data = data
            
            article = TempArticle(article_data)
        else:
            raise HTTPException(status_code=404, detail="Article not found in PubMed")
    
    insights = ai_service.generate_medical_affairs_insights(article)
    
    # Convert article to a serializable format for the response
    if hasattr(article, 'raw_data'):
        # This is a TempArticle from PubMed
        article_response = article.raw_data
    else:
        # This is a database article - convert to dict
        article_response = {
            "pubmed_id": article.pubmed_id,
            "title": article.title,
            "abstract": article.abstract,
            "authors": article.authors if isinstance(article.authors, list) else json.loads(article.authors or "[]"),
            "journal": article.journal,
            "publication_date": article.publication_date,
            "therapeutic_area": article.therapeutic_area,
            "link": article.link,
            "created_at": article.created_at.isoformat() if hasattr(article, 'created_at') and article.created_at else None,
            "id": getattr(article, 'id', None),
            "rss_fetch_date": getattr(article, 'rss_fetch_date', None),
            # "insights": getattr(article, 'insights', None)  # Temporarily disabled
        }
    
    return {"insights": insights, "article": article_response}

# Save feature temporarily removed - focusing on search and insights generation only

# Conversation endpoints
@app.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    db: Session = Depends(get_db)
):
    conversation_service = ConversationService(db)
    conversations = conversation_service.get_all_conversations()
    return conversations

@app.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db)
):
    conversation_service = ConversationService(db)
    return conversation_service.create_conversation(conversation)

@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    conversation_service = ConversationService(db)
    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@app.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    title: str,
    db: Session = Depends(get_db)
):
    conversation_service = ConversationService(db)
    return conversation_service.rename_conversation(conversation_id, title)

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    conversation_service = ConversationService(db)
    conversation_service.delete_conversation(conversation_id)
    return {"message": "Conversation deleted"}

# Message endpoints
@app.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    conversation_service = ConversationService(db)
    messages = conversation_service.get_conversation_messages(conversation_id)
    return messages

@app.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: int,
    message: MessageCreate,
    db: Session = Depends(get_db)
):
    conversation_service = ConversationService(db)
    return conversation_service.add_message(conversation_id, message)

# Debug endpoint
@app.get("/debug/pubmed-speed/{therapeutic_area}")
async def debug_pubmed_speed(therapeutic_area: str):
    """Debug endpoint to test PubMed speed"""
    import time
    start_time = time.time()
    
    try:
        articles = cached_pubmed_search(therapeutic_area, 7)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return {
            "search_term": therapeutic_area,
            "total_time_seconds": round(total_time, 2),
            "articles_found": len(articles),
            "articles_per_second": round(len(articles) / total_time, 2) if total_time > 0 else 0,
            "first_article_title": articles[0]["title"] if articles else "No articles"
        }
    except Exception as e:
        end_time = time.time()
        return {
            "error": str(e),
            "total_time_seconds": round(end_time - start_time, 2)
        }

# Debug endpoints for database management
@app.get("/debug/db-count")
async def debug_db_count(db: Session = Depends(get_db)):
    """Debug endpoint to check article count in database"""
    from models import Article
    count = db.query(Article).count()
    return {"article_count": count}

@app.post("/debug/clear-db")
async def debug_clear_db(db: Session = Depends(get_db)):
    """Debug endpoint to clear all articles from database"""
    from models import Article
    count = db.query(Article).count()
    db.query(Article).delete()
    db.commit()
    return {"message": f"Cleared {count} articles from database", "articles_cleared": count}

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
