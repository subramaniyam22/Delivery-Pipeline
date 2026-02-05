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
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default: 100 requests per minute
    storage_uri="redis://localhost:6379",  # Will use REDIS_URL from env
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
