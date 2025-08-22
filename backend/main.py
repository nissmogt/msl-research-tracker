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
    FetchPubmedRequest
)
from services import (
    ArticleService, ConversationService, AIService
)
from pubmed_service import PubMedService

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MSL Research Tracker API",
    description="Medical Science Liaison Research Tracking and Insights Platform",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://msl-research-tracker.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
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
            "port": os.environ.get("PORT", "unknown"),
            "database_url": "configured" if os.environ.get("DATABASE_URL") else "missing",
            "openai_api": "configured" if os.environ.get("OPENAI_API_KEY") else "missing",
            "secret_key": "configured" if os.environ.get("SECRET_KEY") else "generated"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": f"error: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "port": os.environ.get("PORT", "unknown"),
            "database_url": "configured" if os.environ.get("DATABASE_URL") else "missing",
            "openai_api": "configured" if os.environ.get("OPENAI_API_KEY") else "missing",
            "secret_key": "configured" if os.environ.get("SECRET_KEY") else "generated"
        }

@app.get("/")
async def root():
    return {
        "message": "MSL Research Tracker API",
        "status": "running",
        "version": "1.0.0"
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
    
    # Sort by journal impact factor for reliability
    return sort_by_impact_factor(articles)

def sort_by_impact_factor(articles):
    """
    Sort articles by journal impact factor for reliability assessment
    High-impact journals = more reliable insights
    """
    # Journal impact factor database (2023 data)
    JOURNAL_IMPACT_FACTORS = {
        # Tier 1: Top medical journals (IF > 50)
        'nature': 64.8, 'nature medicine': 87.2, 'science': 63.7,
        'new england journal of medicine': 176.1, 'nejm': 176.1,
        'lancet': 168.9, 'cell': 64.5, 'jama': 157.3,
        
        # Tier 2: High-impact specialty journals (IF 10-50)
        'nature genetics': 41.3, 'nature biotechnology': 54.9,
        'cancer cell': 50.3, 'cell metabolism': 31.4,
        'circulation': 37.8, 'blood': 25.4, 'diabetes': 9.8,
        'neuron': 16.2, 'immunity': 43.5, 'gastroenterology': 29.4,
        
        # Tier 3: Good specialty journals (IF 5-10)
        'plos medicine': 13.8, 'bmj': 105.7, 'clinical cancer research': 13.8,
        'journal of clinical investigation': 15.9, 'jci': 15.9,
        'american journal of gastroenterology': 9.8,
        'european heart journal': 35.3,
        
        # Tier 4: Standard journals (IF 2-5)
        'plos one': 3.7, 'scientific reports': 4.6,
        'bmc medicine': 9.3, 'medicine': 1.6,
        
        # Default for unknown journals
        'unknown': 1.0
    }
    
    def get_impact_factor(journal_name):
        """Get impact factor for a journal (case-insensitive)"""
        if not journal_name:
            return 1.0
        
        journal_lower = journal_name.lower().strip()
        
        # Direct match
        if journal_lower in JOURNAL_IMPACT_FACTORS:
            return JOURNAL_IMPACT_FACTORS[journal_lower]
        
        # Partial match for journal names with variations
        for journal_key, impact_factor in JOURNAL_IMPACT_FACTORS.items():
            if journal_key in journal_lower or journal_lower in journal_key:
                return impact_factor
        
        # Unknown journal - assign low impact factor
        return 1.0
    
    # Add impact factor to each article and sort
    for article in articles:
        article['impact_factor'] = get_impact_factor(article.get('journal', ''))
        article['reliability_tier'] = get_reliability_tier(article['impact_factor'])
    
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
async def search_articles(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    article_service = ArticleService(db)
    
    # First, search local database
    articles = article_service.search_articles(request.therapeutic_area, request.days_back)
    
    # If no articles found locally, try to fetch from PubMed
    if not articles:
        pubmed_service = PubMedService()
        pubmed_articles = pubmed_service.search_articles(request.therapeutic_area, request.days_back)
        if pubmed_articles:
            saved_count = pubmed_service.save_articles_to_db(db, pubmed_articles)
            # Re-query the database to get the saved articles
            articles = article_service.search_articles(request.therapeutic_area, request.days_back)
    
    return articles

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
async def search_pubmed_only(request: SearchRequest):
    """Search PubMed with caching for speed"""
    try:
        articles = cached_pubmed_search(request.therapeutic_area, request.days_back)
        
        # Convert to response format
        response_articles = []
        for article_data in articles:
            response_articles.append({
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
                "impact_factor": article_data.get('impact_factor', 1.0),
                "reliability_tier": article_data.get('reliability_tier', 'Unknown')
            })
        
        return response_articles
    except Exception as e:
        print(f"Error in cached search: {e}")
        return []

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

# AI Insights endpoints
@app.post("/articles/{pubmed_id}/insights")
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

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
