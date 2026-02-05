"""
Enhanced dependencies with detailed logging for debugging.
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import decode_access_token
from app.models import User
from typing import Optional
import logging
import time

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)  # Don't auto-error, handle manually


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token with detailed logging"""
    start_time = time.time()
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.info(f"[{request_id}] get_current_user started")
    
    # Check if credentials provided
    if not credentials:
        logger.warning(f"[{request_id}] No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    logger.info(f"[{request_id}] Token received, length: {len(token)}")
    
    # Decode token
    decode_start = time.time()
    payload = decode_access_token(token)
    decode_time = time.time() - decode_start
    logger.info(f"[{request_id}] Token decode took {decode_time:.3f}s")
    
    if payload is None:
        logger.error(f"[{request_id}] Token decode failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    if email is None:
        logger.error(f"[{request_id}] No email in token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"[{request_id}] Looking up user: {email}")
    
    # Query user
    query_start = time.time()
    user = db.query(User).filter(User.email == email).first()
    query_time = time.time() - query_start
    logger.info(f"[{request_id}] User query took {query_time:.3f}s")
    
    if user is None:
        logger.error(f"[{request_id}] User not found: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    total_time = time.time() - start_time
    logger.info(f"[{request_id}] get_current_user completed in {total_time:.3f}s")
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# Keep old version for compatibility
def get_current_user_from_token(token: str, db: Session) -> Optional[User]:
    """Legacy function for WebSocket authentication"""
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    email = payload.get("sub")
    if email is None:
        return None
    
    return db.query(User).filter(User.email == email).first()
