"""
Centralized error handling and custom exceptions for the application.
"""
import re
import logging
from typing import Optional, Dict, Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)


def _cors_allow_origin(request: Request) -> str:
    """Return the origin to set in Access-Control-Allow-Origin (must match request or first allowed)."""
    origin = request.headers.get("origin") or ""
    allowed = list(settings.cors_origins_list)
    if settings.FRONTEND_URL and settings.FRONTEND_URL not in allowed:
        allowed.append(settings.FRONTEND_URL)
    if origin and origin in allowed:
        return origin
    regex = getattr(settings, "CORS_ORIGIN_REGEX", None) or ""
    if origin and regex and re.match(regex, origin):
        return origin
    return (allowed[0] if allowed else "") or (settings.FRONTEND_URL or "*")


class AppException(Exception):
    """Base exception class for application-specific errors."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Raised when input validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class AuthenticationError(AppException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            error_code="AUTHENTICATION_ERROR",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(AppException):
    """Raised when user lacks permission."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            error_code="AUTHORIZATION_ERROR",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class NotFoundError(AppException):
    """Raised when resource is not found."""
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            error_code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier}
        )


class ConflictError(AppException):
    """Raised when there's a conflict (e.g., duplicate resource)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class BusinessLogicError(AppException):
    """Raised when business logic validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="BUSINESS_LOGIC_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application-specific exceptions."""
    logger.warning(
        f"AppException: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with consistent format."""
    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": exc.detail,
            "details": {}
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    
    allow_origin = _cors_allow_origin(request)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": f"An unexpected error occurred: {str(exc)}",  # DEBUG: Exposed error
            "details": {}
        },
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )
