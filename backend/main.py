from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import json
import os

from database import get_db, engine
from models import Base
from schemas import (
    ArticleResponse, SearchRequest,
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse,
    InsightRequest
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
        "http://localhost:3000",
        "https://msl-research-tracker.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "MSL Research Tracker API"}

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
    therapeutic_area: str,
    days_back: int = 7,
    db: Session = Depends(get_db)
):
    pubmed_service = PubMedService()
    articles = pubmed_service.search_articles(therapeutic_area, days_back)
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 