"""
Provider adapters for external services with caching
Implements embedding cache using the EmbeddingCache table with SQLAlchemy 2.0 patterns
"""

import json
import hashlib
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from openai import OpenAI
from models import EmbeddingCache
from config import settings

class EmbeddingProvider:
    """
    OpenAI embedding provider with SQLAlchemy-based caching
    Dramatically reduces API costs by caching embedding vectors
    """
    
    def __init__(self, db: Session, model: str = "text-embedding-3-large"):
        self.db = db
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = model
        self.cache_hits = 0
        self.cache_misses = 0

    def encode(self, text: str) -> List[float]:
        """
        Get embedding vector for text with automatic caching
        Returns cached result if available, otherwise calls OpenAI API
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured - set OPENAI_API_KEY environment variable")
        
        # Generate cache key
        cache_key = self._generate_cache_key(text)
        
        # Try cache first (SQLAlchemy 2.0 pattern)
        stmt = select(EmbeddingCache).where(EmbeddingCache.content_hash == cache_key)
        cached_row = self.db.execute(stmt).scalar_one_or_none()
        
        if cached_row:
            self.cache_hits += 1
            # Update access tracking
            cached_row.access_count += 1
            cached_row.accessed_at = func.now()
            self.db.commit()
            
            return json.loads(cached_row.embedding_vector)
        
        # Cache miss: call OpenAI API
        self.cache_misses += 1
        vector = self._call_openai_api(text)
        
        # Store in cache
        cache_entry = EmbeddingCache(
            content_hash=cache_key,
            content_type="text_general",
            embedding_vector=json.dumps(vector),
            embedding_model=self.model,
            access_count=1
        )
        self.db.add(cache_entry)
        self.db.commit()
        
        return vector

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch encode multiple texts for efficiency
        Uses cache for individual texts, batch API call for misses
        """
        results = []
        cache_misses = []
        cache_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            cache_key = self._generate_cache_key(text)
            stmt = select(EmbeddingCache).where(EmbeddingCache.content_hash == cache_key)
            cached_row = self.db.execute(stmt).scalar_one_or_none()
            
            if cached_row:
                results.append(json.loads(cached_row.embedding_vector))
                self.cache_hits += 1
                # Update access tracking
                cached_row.access_count += 1
                cached_row.accessed_at = func.now()
            else:
                results.append(None)  # Placeholder
                cache_misses.append(text)
                cache_indices.append(i)
        
        # Batch call for cache misses
        if cache_misses:
            if not self.client:
                raise ValueError("OpenAI API key not configured")
            
            batch_vectors = self._call_openai_batch(cache_misses)
            
            # Fill in results and update cache
            for j, vector in enumerate(batch_vectors):
                original_index = cache_indices[j]
                results[original_index] = vector
                
                # Cache the result
                cache_key = self._generate_cache_key(cache_misses[j])
                cache_entry = EmbeddingCache(
                    content_hash=cache_key,
                    content_type="text_batch",
                    embedding_vector=json.dumps(vector),
                    embedding_model=self.model,
                    access_count=1
                )
                self.db.add(cache_entry)
            
            self.db.commit()
            self.cache_misses += len(cache_misses)
        
        return results

    def get_cache_stats(self) -> dict:
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }

    def _generate_cache_key(self, text: str) -> str:
        """Generate consistent cache key for text"""
        content = f"{self.model}::{text}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _call_openai_api(self, text: str) -> List[float]:
        """Call OpenAI API for single text"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"OpenAI API error: {e}")
            raise

    def _call_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """Call OpenAI API for batch of texts"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"OpenAI batch API error: {e}")
            raise

# Utility function for computing cosine similarity
def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two embedding vectors"""
    import math
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)
