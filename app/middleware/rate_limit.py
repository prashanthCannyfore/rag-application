"""
Rate limiting middleware for API protection
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    def _cleanup_old_requests(self, key: str):
        """Remove requests older than 1 minute"""
        cutoff = time.time() - 60
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
    
    def _is_rate_limited(self, key: str) -> tuple[bool, int]:
        """Check if request should be rate limited"""
        self._cleanup_old_requests(key)
        
        if len(self.requests[key]) >= self.requests_per_minute:
            return True, self.requests_per_minute
        
        self.requests[key].append(time.time())
        return False, len(self.requests[key])
    
    def check_rate_limit(self, key: str) -> tuple[bool, int, int]:
        """Check rate limit and return status"""
        limited, current = self._is_rate_limited(key)
        remaining = self.requests_per_minute - current
        return limited, current, remaining

# Global rate limiter
rate_limiter = RateLimiter(requests_per_minute=60)

# API-specific rate limits
api_rate_limiter = RateLimiter(requests_per_minute=30)
chat_rate_limiter = RateLimiter(requests_per_minute=20)
auth_rate_limiter = RateLimiter(requests_per_minute=5)

async def rate_limit_middleware(request: Request, call_next):
    """Middleware to apply rate limiting"""
    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    # Get client identifier
    client_ip = request.client.host if request.client else "unknown"
    user_id = request.headers.get("X-User-ID", client_ip)
    key = f"{user_id}:{request.url.path}"
    
    # Choose rate limiter based on endpoint
    if "/auth/" in request.url.path:
        limiter = auth_rate_limiter
    elif "/chat" in request.url.path:
        limiter = chat_rate_limiter
    else:
        limiter = api_rate_limiter
    
    limited, current, remaining = limiter.check_rate_limit(key)
    
    # Add rate limit headers
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
    
    if limited:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again in a minute.",
                "retry_after": 60
            },
            headers=response.headers
        )
    
    return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for rate limiting"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rate_limiter = RateLimiter(requests_per_minute)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/openapi.json", "/"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_id = request.headers.get("X-User-ID", client_ip)
        key = f"{user_id}:{request.url.path}"
        
        # Check rate limit
        limited, current, remaining = self.rate_limiter.check_rate_limit(key)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        
        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again in a minute.",
                    "retry_after": 60
                },
                headers=response.headers
            )
        
        return response