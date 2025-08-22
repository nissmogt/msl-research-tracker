from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import uvicorn
import json
import os
from datetime import datetime
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib
import threading

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    try:
        # Test database connection
        db = next(get_db())
        result = db.execute("SELECT 1").fetchone()
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
            "port": os.environ.get("PORT", "unknown"),
            "database_url": "configured" if os.environ.get("DATABASE_URL") else "missing"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": f"error: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "port": os.environ.get("PORT", "unknown"),
            "database_url": "configured" if os.environ.get("DATABASE_URL") else "missing"
        }

@app.get("/")
async def root():
    return {
        "message": "MSL Research Tracker API",
        "status": "running",
        "version": "1.0.0"
    }

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

# PubMed integration endpoints
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

# Cache responses for 1 hour
@lru_cache(maxsize=100)
def cached_pubmed_search(search_key: str):
    """Cache PubMed searches to avoid repeated slow API calls"""
    pubmed_service = PubMedService()
    # Parse the search key back to parameters
    therapeutic_area, days_back = search_key.split("|")
    return pubmed_service.search_articles(therapeutic_area, int(days_back))

@app.post("/articles/search-pubmed")
async def search_pubmed_only(request: SearchRequest):
    """Search PubMed with caching for speed"""
    # Create cache key
    cache_key = f"{request.therapeutic_area}|{request.days_back}"
    
    try:
        articles = cached_pubmed_search(cache_key)
        
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
            "created_at": None
        })
    
    return response_articles
    except Exception as e:
        print(f"Error in cached search: {e}")
        return []

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

# Conversation endpoints (global, not user-specific)
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

# Message endpoints (global, not user-specific)
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

## **The Real Solution: Caching + Pagination**

Since PubMed API is inherently slow, let's make it feel fast with smart caching:

### **Solution 1: Add Response Caching**

```python:backend/main.py
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib

# Cache responses for 1 hour
@lru_cache(maxsize=100)
def cached_pubmed_search(search_key: str):
    """Cache PubMed searches to avoid repeated slow API calls"""
    pubmed_service = PubMedService()
    # Parse the search key back to parameters
    therapeutic_area, days_back = search_key.split("|")
    return pubmed_service.search_articles(therapeutic_area, int(days_back))

@app.post("/articles/search-pubmed")
async def search_pubmed_only(request: SearchRequest):
    """Search PubMed with caching for speed"""
    # Create cache key
    cache_key = f"{request.therapeutic_area}|{request.days_back}"
    
    try:
        articles = cached_pubmed_search(cache_key)
        
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
                "created_at": None
            })
        
        return response_articles
    except Exception as e:
        print(f"Error in cached search: {e}")
        return []
```

### **Solution 2: Add Loading Indicators**

Update the frontend to show progress:

```javascript:frontend/src/components/Dashboard.js
const [searchStatus, setSearchStatus] = useState('');
const [searchProgress, setSearchProgress] = useState(0);

const handleSearch = async () => {
  if (!searchTerm.trim()) return;
  setLoading(true);
  setSearchProgress(0);
  
  try {
    const endpoint = searchMode === 'pubmed' ? '/articles/search-pubmed' : '/articles/search';
    
    if (searchMode === 'pubmed') {
      setSearchStatus('Searching PubMed (this may take 15+ seconds)...');
      
      // Show progress animation
      const progressInterval = setInterval(() => {
        setSearchProgress(prev => {
          if (prev >= 90) return prev;
          return prev + Math.random() * 10;
        });
      }, 500);
      
      const response = await axios.post(endpoint, {
        therapeutic_area: searchTerm,
        days_back: daysBack
      });
      
      clearInterval(progressInterval);
      setSearchProgress(100);
    } else {
      setSearchStatus('Searching local database...');
      const response = await axios.post(endpoint, {
        therapeutic_area: searchTerm,
        days_back: daysBack
      });
    }
    
    setArticles(response.data);
    setSearchStatus('');
    setSearchProgress(0);
  } catch (error) {
    console.error('[Dashboard] Error searching articles:', error);
    setSearchStatus('Search failed');
    setSearchProgress(0);
  }
  setLoading(false);
};

// In your JSX:
{loading && (
  <div className="text-center p-4">
    <div className="w-full bg-gray-200 rounded-full h-2.5 mb-4">
      <div 
        className="bg-primary-600 h-2.5 rounded-full transition-all duration-500" 
        style={{ width: `${searchProgress}%` }}
      ></div>
    </div>
    <p className="text-sm text-gray-600">{searchStatus}</p>
    <p className="text-xs text-gray-500 mt-1">
      PubMed searches can take 10-20 seconds due to API limitations
    </p>
  </div>
)}
```

### **Solution 3: Background Pre-fetching**

Add popular searches in background:

```python:backend/main.py
<code_block_to_apply_changes_from>
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

## **The
```

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import uvicorn
import json
import os
from datetime import datetime
from functools import lru_cache

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    try:
        # Test database connection
        db = next(get_db())
        result = db.execute("SELECT 1").fetchone()
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
            "port": os.environ.get("PORT", "unknown"),
            "database_url": "configured" if os.environ.get("DATABASE_URL") else "missing"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": f"error: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "port": os.environ.get("PORT", "unknown"),
            "database_url": "configured" if os.environ.get("DATABASE_URL") else "missing"
        }

@app.get("/")
async def root():
    return {
        "message": "MSL Research Tracker API",
        "status": "running",
        "version": "1.0.0"
    }

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

# PubMed integration endpoints
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

@app.post("/articles/search-pubmed")
async def search_pubmed_only(
    request: SearchRequest
):
    """Search PubMed directly without saving to database"""
    pubmed_service = PubMedService()
    articles = pubmed_service.search_articles(request.therapeutic_area, request.days_back)
    
    # Convert articles to response format
    response_articles = []
    for article_data in articles:
        # Convert authors list to JSON string for consistency
        authors_json = json.dumps(article_data['authors']) if isinstance(article_data['authors'], list) else article_data['authors']
        
        response_articles.append({
            "id": None,  # Not saved to DB yet
            "pubmed_id": article_data['pubmed_id'],
            "title": article_data['title'],
            "authors": article_data['authors'],  # Keep as list for response
            "abstract": article_data['abstract'],
            "publication_date": article_data['publication_date'],
            "journal": article_data['journal'],
            "therapeutic_area": article_data['therapeutic_area'],
            "link": article_data['link'],
            "created_at": None
        })
    
    return response_articles

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

# Conversation endpoints (global, not user-specific)
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

# Message endpoints (global, not user-specific)
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
@lru_cache(maxsize=100)
def cached_pubmed_search(therapeutic_area: str, days_back: int):
    pubmed_service = PubMedService()
    return pubmed_service.search_articles(therapeutic_area, days_back) 
