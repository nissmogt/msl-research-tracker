from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class TherapeuticArea(Base):
    __tablename__ = "therapeutic_areas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    
    conversations = relationship("Conversation", back_populates="therapeutic_area")

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    pubmed_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    authors = Column(Text)  # JSON string
    abstract = Column(Text)
    publication_date = Column(String)
    journal = Column(String)
    therapeutic_area = Column(String)
    link = Column(String)
    rss_fetch_date = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    ta_id = Column(Integer, ForeignKey("therapeutic_areas.id"), nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    therapeutic_area = relationship("TherapeuticArea", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_ai = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="messages") 