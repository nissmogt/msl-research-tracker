from sqlalchemy.orm import Session
from typing import List, Optional
import json
import requests
from datetime import datetime, timedelta
import openai
import os
from dotenv import load_dotenv

from models import Article, Conversation, Message, TherapeuticArea
from schemas import ConversationCreate, MessageCreate
from config import settings

load_dotenv()

# OpenAI configuration
openai.api_key = settings.OPENAI_API_KEY

class ArticleService:
    def __init__(self, db: Session):
        self.db = db
    
    def search_articles(self, therapeutic_area: str, days_back: int = 7) -> List[Article]:
        """Search PubMed for articles in the specified therapeutic area"""
        # This is a simplified version - in production, you'd use PubMed E-utilities
        # For now, we'll return articles from our database
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        articles = self.db.query(Article).filter(
            Article.therapeutic_area == therapeutic_area,
            Article.created_at >= cutoff_date
        ).order_by(Article.created_at.desc()).all()
        
        return articles
    
    def get_recent_articles(self, therapeutic_area: Optional[str] = None, days_back: int = 7) -> List[Article]:
        """Get recent articles from database"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        query = self.db.query(Article).filter(Article.created_at >= cutoff_date)
        
        if therapeutic_area:
            query = query.filter(Article.therapeutic_area == therapeutic_area)
        
        return query.order_by(Article.created_at.desc()).all()
    
    def get_article_by_pubmed_id(self, pubmed_id: str) -> Optional[Article]:
        """Get article by PubMed ID"""
        return self.db.query(Article).filter(Article.pubmed_id == pubmed_id).first()
    
    def fetch_from_pubmed(self, therapeutic_area: str, days_back: int = 7):
        """Fetch articles from PubMed RSS feed"""
        # This would integrate with your existing pubmed_rss.py logic
        # For now, this is a placeholder
        pass

class ConversationService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_conversations(self) -> List[Conversation]:
        """Get all conversations (global)"""
        return self.db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    
    def create_conversation(self, conversation: ConversationCreate) -> Conversation:
        """Create a new conversation"""
        db_conversation = Conversation(
            ta_id=conversation.ta_id,
            title=conversation.title
        )
        self.db.add(db_conversation)
        self.db.commit()
        self.db.refresh(db_conversation)
        return db_conversation
    
    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a specific conversation"""
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
    
    def rename_conversation(self, conversation_id: int, title: str) -> Conversation:
        """Rename a conversation"""
        conversation = self.get_conversation(conversation_id)
        if conversation:
            conversation.title = title
            self.db.commit()
            self.db.refresh(conversation)
        return conversation
    
    def delete_conversation(self, conversation_id: int):
        """Delete a conversation"""
        conversation = self.get_conversation(conversation_id)
        if conversation:
            self.db.delete(conversation)
            self.db.commit()
    
    def get_conversation_messages(self, conversation_id: int) -> List[Message]:
        """Get all messages for a conversation"""
        # First verify the conversation exists
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
    
    def add_message(self, conversation_id: int, message: MessageCreate) -> Message:
        """Add a message to a conversation"""
        # Verify the conversation exists
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        
        db_message = Message(
            conversation_id=conversation_id,
            content=message.content,
            is_ai=message.is_ai
        )
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

class AIService:
    def __init__(self):
        self.client = openai.OpenAI()
    
    def generate_medical_affairs_insights(self, article: Article) -> str:
        """Generate medical affairs insights for an article"""
        try:
            # Handle authors field - convert from JSON string to list if needed
            authors = article.authors
            if isinstance(authors, str):
                try:
                    authors = json.loads(authors)
                except (json.JSONDecodeError, TypeError):
                    authors = []
            
            authors_text = ", ".join(authors) if isinstance(authors, list) else str(authors)
            
            prompt = f"""
            As a Medical Science Liaison (MSL), analyze this research article and provide insights:

            Title: {article.title}
            Authors: {authors_text}
            Abstract: {article.abstract}
            Journal: {article.journal}
            Publication Date: {article.publication_date}

            Please provide:
            1. Key findings and clinical implications
            2. Relevance to medical affairs activities
            3. Potential impact on clinical practice
            4. Questions for KOL discussions
            5. Action items for MSL team

            Format your response in a clear, structured manner suitable for medical affairs professionals.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert Medical Science Liaison with deep knowledge of clinical research and medical affairs."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating insights: {str(e)}"
    
    def generate_conversation_response(self, conversation_history: List[Message], user_message: str) -> str:
        """Generate AI response for conversation"""
        try:
            # Build conversation context
            context = "You are an AI assistant helping Medical Science Liaisons with research analysis and insights.\n\n"
            
            for msg in conversation_history:
                role = "assistant" if msg.is_ai else "user"
                context += f"{role}: {msg.content}\n"
            
            context += f"user: {user_message}\nassistant:"
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert Medical Science Liaison assistant. Provide helpful, accurate, and professional responses."},
                    {"role": "user", "content": context}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}" 