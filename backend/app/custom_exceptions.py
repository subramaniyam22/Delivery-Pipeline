"""
Custom exception classes for standardized error handling.
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class AppException(HTTPException):
    """Base exception for all application exceptions"""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}


class NotFoundException(AppException):
    """Resource not found exception"""
    def __init__(self, detail: str = "Resource not found", resource_type: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND",
            extra={"resource_type": resource_type} if resource_type else {}
        )


class ValidationException(AppException):
    """Validation error exception"""
    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="VALIDATION_ERROR",
            extra={"field": field} if field else {}
        )


class UnauthorizedException(AppException):
    """Unauthorized access exception"""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED"
        )


class ForbiddenException(AppException):
    """Forbidden access exception"""
    def __init__(self, detail: str = "Forbidden", required_role: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN",
            extra={"required_role": required_role} if required_role else {}
        )


class ConflictException(AppException):
    """Resource conflict exception"""
    def __init__(self, detail: str, resource_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT",
            extra={"resource_id": resource_id} if resource_id else {}
        )


class DatabaseException(AppException):
    """Database operation exception"""
    def __init__(self, detail: str = "Database error occurred"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR"
        )


class ExternalServiceException(AppException):
    """External service error exception"""
    def __init__(self, detail: str, service_name: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="EXTERNAL_SERVICE_ERROR",
            extra={"service": service_name} if service_name else {}
        )


class RateLimitException(AppException):
    """Rate limit exceeded exception"""
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            extra={"retry_after": retry_after} if retry_after else {}
        )


# Standardized error response format
def format_error_response(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400
) -> Dict[str, Any]:
    """
    Format error response in standardized format.
    
    Returns:
        {
            "error": {
                "code": "ERROR_CODE",
                "message": "Human readable message",
                "details": {...},
                "status": 400
            }
        }
    """
    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
            "status": status_code
        }
    }
