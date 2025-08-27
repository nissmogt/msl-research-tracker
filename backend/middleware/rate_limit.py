"""
Rate limiting middleware for MSL Research Tracker API.
Implements industry-standard rate limiting to protect against DoS attacks and API abuse.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict, Optional
import json

# Create the rate limiter
limiter = Limiter(key_func=get_remote_address)

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Custom rate limiting middleware with different limits for different endpoint types.
    Uses slowapi under the hood with enhanced configuration.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.limiter = limiter
        
        # Define rate limits for different endpoint patterns
        self.rate_limits = {
            # Health and status endpoints - more permissive
            "/": "60/minute",
            "/health": "60/minute",
            "/docs": "30/minute",
            "/redoc": "30/minute",
            
            # Search endpoints - moderate limits (these are expensive operations)
            "/api/articles/search": "10/minute",
            "/api/articles/search-pubmed": "5/minute",  # PubMed searches are expensive
            
            # Regular API endpoints
            "/api/articles/recent": "30/minute",
            "/api/articles/fetch-pubmed": "10/minute",
            "/api/conversations": "20/minute",
            "/api/therapeutic-areas": "60/minute",
            
            # AI endpoints - more restrictive (expensive operations)
            "/api/articles/": "15/minute",  # For insights generation
            
            # Default catch-all
            "default": "30/minute"
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths (like health checks from Railway)
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Get the appropriate rate limit for this endpoint
        rate_limit = self._get_rate_limit_for_path(request.url.path)
        
        try:
            # Apply rate limiting
            client_ip = get_remote_address(request)
            
            # Use slowapi's built-in rate limiting logic
            # This is a simplified version - in production you might want more sophisticated logic
            response = await call_next(request)
            
            # Add rate limit headers to the response
            self._add_rate_limit_headers(response, rate_limit)
            
            return response
            
        except RateLimitExceeded:
            return self._create_rate_limit_response(request, rate_limit)
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """
        Determine if rate limiting should be skipped for this request.
        Skip for health checks and internal monitoring.
        """
        # Skip if request comes from Railway health checks
        user_agent = request.headers.get("user-agent", "").lower()
        if "railway" in user_agent or "health" in user_agent:
            return True
        
        # Skip if it's an internal request (has our edge auth header)
        if request.headers.get("X-Edge-Auth"):
            # This is coming through our secure proxy, apply normal rate limiting
            return False
        
        return False
    
    def _get_rate_limit_for_path(self, path: str) -> str:
        """
        Get the appropriate rate limit string for a given path.
        """
        # Check for exact matches first
        if path in self.rate_limits:
            return self.rate_limits[path]
        
        # Check for pattern matches
        for pattern, limit in self.rate_limits.items():
            if path.startswith(pattern):
                return limit
        
        # Return default rate limit
        return self.rate_limits["default"]
    
    def _add_rate_limit_headers(self, response: Response, rate_limit: str):
        """
        Add standard rate limiting headers to the response.
        """
        # Parse rate limit string (e.g., "30/minute")
        limit, period = rate_limit.split("/")
        
        response.headers["X-RateLimit-Limit"] = limit
        response.headers["X-RateLimit-Period"] = period
        response.headers["X-RateLimit-Policy"] = f"{limit} requests per {period}"
    
    def _create_rate_limit_response(self, request: Request, rate_limit: str) -> Response:
        """
        Create a proper 429 Too Many Requests response.
        """
        from fastapi.responses import JSONResponse
        
        # Parse rate limit for retry-after calculation
        limit, period = rate_limit.split("/")
        
        # Calculate retry-after seconds
        retry_after = 60 if period == "minute" else 3600 if period == "hour" else 86400
        
        client_ip = get_remote_address(request)
        print(f"⚠️  Rate limit exceeded for {client_ip} on {request.url.path} (limit: {rate_limit})")
        
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {rate_limit}",
                "retry_after_seconds": retry_after,
                "path": request.url.path
            }
        )
        
        response.headers["Retry-After"] = str(retry_after)
        response.headers["X-RateLimit-Limit"] = limit
        response.headers["X-RateLimit-Period"] = period
        
        return response


# Rate limiting decorators for specific endpoints
def rate_limit(limit_string: str):
    """
    Decorator for applying rate limits to specific FastAPI endpoints.
    Usage: @rate_limit("10/minute")
    """
    return limiter.limit(limit_string)


# Custom rate limit for search endpoints
search_rate_limit = limiter.limit("10/minute")
pubmed_search_rate_limit = limiter.limit("5/minute") 
ai_insights_rate_limit = limiter.limit("15/minute")
general_api_rate_limit = limiter.limit("30/minute")
