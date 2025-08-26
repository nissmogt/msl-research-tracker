"""
Edge authentication middleware for validating requests from Vercel proxy.
This middleware ensures that only requests with the correct X-Edge-Auth header
(injected by our Vercel serverless function) can access the API.
"""

import os
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

class EdgeAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate X-Edge-Auth header from Vercel proxy.
    Blocks direct access to Railway backend without the secret header.
    """
    
    def __init__(self, app, excluded_paths: list = None):
        super().__init__(app)
        self.edge_secret = os.getenv("EDGE_SECRET")
        self.excluded_paths = excluded_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for excluded paths (health checks, docs, etc.)
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
            
        # Check if EDGE_SECRET is configured
        if not self.edge_secret:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Server misconfiguration: EDGE_SECRET not set"}
            )
        
        # Validate X-Edge-Auth header
        edge_auth_header = request.headers.get("X-Edge-Auth")
        
        if not edge_auth_header or edge_auth_header != self.edge_secret:
            # Log the unauthorized attempt for monitoring
            client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
            print(f"⚠️  Unauthorized access attempt from {client_ip} to {request.url.path}")
            
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Forbidden: Direct access not allowed"}
            )
        
        # Valid request - proceed
        return await call_next(request)


def require_edge_auth_dependency():
    """
    FastAPI dependency function for route-level protection.
    Use this as an alternative to the middleware for specific routes.
    """
    def _require_edge_auth(request: Request):
        edge_secret = os.getenv("EDGE_SECRET")
        
        if not edge_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server misconfiguration: EDGE_SECRET not set"
            )
        
        edge_auth_header = request.headers.get("X-Edge-Auth")
        
        if not edge_auth_header or edge_auth_header != edge_secret:
            client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
            print(f"⚠️  Unauthorized access attempt from {client_ip} to {request.url.path}")
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Direct access not allowed"
            )
        
        return True
    
    return _require_edge_auth
