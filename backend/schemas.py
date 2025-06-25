from pydantic import BaseModel, field_validator
from typing import List, Optional, Union
from datetime import datetime
import json

# Article schemas
class ArticleBase(BaseModel):
    pubmed_id: str
    title: str
    authors: Union[str, List[str]]  # Can be JSON string from DB or list from API
    abstract: str
    publication_date: str
    journal: Optional[str] = None
    therapeutic_area: Optional[str] = None
    link: Optional[str] = None

class ArticleResponse(ArticleBase):
    id: int
    created_at: datetime
    authors: List[str]  # Always return as list
    
    @field_validator('authors', mode='before')
    @classmethod
    def parse_authors(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        elif isinstance(v, list):
            return v
        else:
            return []
    
    @field_validator('abstract', mode='before')
    @classmethod
    def ensure_abstract_string(cls, v):
        if v is None:
            return ''
        return str(v)
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    therapeutic_area: str
    days_back: int = 7

class InsightRequest(BaseModel):
    pass  # No additional fields needed for now

# Conversation schemas
class ConversationBase(BaseModel):
    title: str
    ta_id: int

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Message schemas
class MessageBase(BaseModel):
    content: str
    is_ai: bool = False

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True 