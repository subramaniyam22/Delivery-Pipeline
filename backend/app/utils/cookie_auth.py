"""
Secure JWT authentication with httpOnly cookies.
"""
from fastapi import Response, Request, HTTPException, status
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.config import settings
from app.auth import create_access_token, decode_access_token

logger = logging.getLogger(__name__)

# Cookie settings
COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600  # Convert to seconds


def set_auth_cookie(response: Response, email: str) -> str:
    """
    Create JWT token and set it as httpOnly cookie.
    
    Args:
        response: FastAPI Response object
        email: User email for token
        
    Returns:
        The access token (for backwards compatibility)
    """
    # Create access token
    access_token = create_access_token(data={"sub": email})
    
    # Determine if we're in production
    is_production = settings.ENVIRONMENT == "production"
    
    # Set httpOnly cookie
    # Note: In development, the cookie will be set by backend (localhost:8000)
    # but won't be accessible from frontend (localhost:3000) due to different origins
    # This is expected - the frontend will continue using localStorage until we update it
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=is_production,  # HTTPS only in production
        samesite="lax",  # Works for same-site requests
        max_age=COOKIE_MAX_AGE,
        path="/"
        # No domain set - cookie will be for the origin that set it
    )
    
    logger.info(f"Auth cookie set for user: {email}")
    
    return access_token


def get_token_from_cookie(request: Request) -> Optional[str]:
    """
    Extract JWT token from httpOnly cookie.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        JWT token if present, None otherwise
    """
    return request.cookies.get(COOKIE_NAME)


def clear_auth_cookie(response: Response):
    """
    Clear authentication cookie (for logout).
    
    Args:
        response: FastAPI Response object
    """
    is_production = settings.ENVIRONMENT == "production"
    
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        domain="localhost" if not is_production else None
    )
    
    logger.info("Auth cookie cleared")


def get_current_user_from_cookie(request: Request) -> dict:
    """
    Get current user from cookie token.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User data from token
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    token = get_token_from_cookie(request)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload
