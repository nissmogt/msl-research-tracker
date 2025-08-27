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
# Rate limiting imports - temporarily disabled until slowapi is installed
# from middleware.rate_limit import RateLimitingMiddleware, limiter, search_rate_limit, pubmed_search_rate_limit, ai_insights_rate_limit
# from slowapi import _rate_limit_exceeded_handler
# from slowapi.errors import RateLimitExceeded

# Create database tables
Base.metadata.create_all(bind=engine)

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

# Add rate limiting to the app - temporarily disabled until slowapi is installed
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add Rate Limiting middleware (before auth middleware) - temporarily disabled
# app.add_middleware(RateLimitingMiddleware)

# Add Edge Authentication middleware to validate X-Edge-Auth header
app.add_middleware(EdgeAuthMiddleware)

# CORS middleware for React frontend - now restricted to insightmsl.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://insightmsl.com",
        "https://www.insightmsl.com",
        "http://localhost:3000",  # Keep for local development
        "http://localhost:3001"   # Keep for local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

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
@app.post("/articles/search", response_model=List[ArticleResponse])
# @search_rate_limit  # Temporarily disabled until slowapi is installed
async def search_articles(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    try:
        article_service = ArticleService(db)
        
        # Search local database only
        articles = article_service.search_articles(request.therapeutic_area, request.days_back)
        print(f"🔍 Local search found {len(articles)} articles for '{request.therapeutic_area}'")
        
        # Recalculate reliability scores based on use case for local articles
        if articles and request.use_case:
            print(f"🔄 Recalculating reliability scores for {len(articles)} local articles with use case: {request.use_case}")
            reliability_meter = ReliabilityMeter()
            from journal_service import JournalImpactFactorService
            journal_service = JournalImpactFactorService()
            
            for article in articles:
                try:
                    use_case_enum = ReliabilityUseCase.CLINICAL if request.use_case.lower() == "clinical" else ReliabilityUseCase.EXPLORATORY
                    impact_factor, _ = journal_service.get_impact_factor(article.journal, db)
                    reliability = reliability_meter.assess_reliability(
                        journal_name=article.journal,
                        therapeutic_area=request.therapeutic_area,
                        use_case=use_case_enum,
                        db=db,
                        impact_factor=impact_factor
                    )
                    # Update article reliability fields
                    article.reliability_score = reliability.score
                    article.reliability_band = reliability.band.value
                    article.reliability_reasons = reliability.reasons
                    article.uncertainty = reliability.uncertainty
                except Exception as e:
                    print(f"❌ Error recalculating reliability for {article.journal}: {e}")
                    
        return articles
    except Exception as e:
        print(f"❌ Error in local article search: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Article search failed: {str(e)}")

@app.get("/articles/recent", response_model=List[ArticleResponse])
async def get_recent_articles(
    therapeutic_area: Optional[str] = None,
    days_back: int = 7,
    db: Session = Depends(get_db)
):
    article_service = ArticleService(db)
    articles = article_service.get_recent_articles(therapeutic_area, days_back)
    return articles

@app.post("/articles/search-pubmed")
# @pubmed_search_rate_limit  # Temporarily disabled until slowapi is installed
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
# @ai_insights_rate_limit  # Temporarily disabled until slowapi is installed
async def generate_insights(
    pubmed_id: str,
    request: InsightRequest,
    db: Session = Depends(get_db)
):
    ai_service = AIService()
    article_service = ArticleService(db)
    article = article_service.get_article_by_pubmed_id(pubmed_id)
    if not article:
        # Try to fetch from PubMed and save
        pubmed_service = PubMedService()
        article_data = pubmed_service._fetch_article_details(pubmed_id)
        if article_data:
            pubmed_service.save_articles_to_db(db, [article_data])
            article = article_service.get_article_by_pubmed_id(pubmed_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    insights = ai_service.generate_medical_affairs_insights(article)
    return {"insights": insights, "article": article}

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
