from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import decode_access_token
from app.models import User
from app.config import settings
from typing import Optional

security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token (header or cookie)"""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    request.state.user_id = str(user.id)
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_current_user_from_token(token: str, db: Session) -> Optional[User]:
    """Get user from token string (for WebSockets)"""
    payload = decode_access_token(token)
    if not payload:
        return None
        
    email: str = payload.get("sub")
    if not email:
        return None
        
    return db.query(User).filter(User.email == email).first()


def _is_trusted_preview_referer(referer: Optional[str]) -> bool:
    """Allow subresource requests (e.g. about.html) when opened from our frontend or from preview index."""
    if not referer:
        return False
    referer = referer.strip()
    if settings.FRONTEND_URL and referer.startswith(settings.FRONTEND_URL.rstrip("/")):
        return True
    for origin in settings.cors_origins_list:
        if origin and referer.startswith(origin.rstrip("/")):
            return True
    if "/api/templates/" in referer and "/preview" in referer:
        return True
    return False


def get_current_user_for_preview(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Auth for preview proxy: token in query (iframe), or header/cookie, or allow if Referer is trusted (subresources like about.html)."""
    token = request.query_params.get("access_token")
    if token:
        user = get_current_user_from_token(token, db)
        if user:
            return user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    referer = request.headers.get("referer") or request.headers.get("Referer")
    if _is_trusted_preview_referer(referer):
        return None
    return get_current_user(request, credentials, db)
