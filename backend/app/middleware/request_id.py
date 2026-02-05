"""
Request ID tracking middleware for distributed tracing.
"""
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each request.
    Useful for distributed tracing and log correlation.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state for access in route handlers
        request.state.request_id = request_id
        
        # Add to logger context
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None
            }
        )
        
        # Process request
        try:
            response: Response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(
                f"Request failed: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True
            )
            raise


def get_request_id(request: Request) -> str:
    """
    Helper function to get request ID from request state.
    
    Usage in route handlers:
        request_id = get_request_id(request)
    """
    return getattr(request.state, "request_id", "unknown")
