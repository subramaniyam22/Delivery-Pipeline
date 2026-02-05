"""
Rate limiting configuration and utilities.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# Initialize rate limiter
import os
from app.config import settings

# Use Redis if explicitly configured, otherwise fallback to memory
redis_url = os.environ.get("REDIS_URL")
storage_uri = redis_url if redis_url else "memory://"

if not redis_url:
    logger.warning("REDIS_URL not set using memory storage for rate limiting")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default: 100 requests per minute
    storage_uri=storage_uri,
    strategy="fixed-window"
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors."""
    logger.warning(
        f"Rate limit exceeded for {get_remote_address(request)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "ip": get_remote_address(request)
        }
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please try again later.",
            "details": {
                "retry_after": "60 seconds"
            }
        }
    )


# Rate limit configurations for different endpoint types
AUTH_RATE_LIMIT = "5/minute"  # Strict limit for auth endpoints
API_RATE_LIMIT = "60/minute"  # Standard API endpoints
UPLOAD_RATE_LIMIT = "10/minute"  # File uploads
