from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import secrets
import logging
from app.db import get_db
from app.models import User, PasswordResetToken
from app.schemas import LoginRequest, Token
from app.auth import verify_password, create_access_token, get_password_hash
from app.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password"""
    user = db.query(User).filter(User.email == request.email).first()
    
    # Debug logging
    print(f"[LOGIN] Attempting login for: {request.email}")
    print(f"[LOGIN] User found: {user is not None}")
    if user:
        print(f"[LOGIN] User active: {user.is_active}")
        password_valid = verify_password(request.password, user.password_hash)
        print(f"[LOGIN] Password valid: {password_valid}")
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return Token(access_token=access_token)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password reset email"""
    logger.info(f"[AUTH] Password reset requested for email: {request.email}")
    
    user = db.query(User).filter(User.email == request.email).first()
    
    # Always return success message to prevent email enumeration
    if not user:
        logger.info(f"[AUTH] No user found with email: {request.email}")
        return MessageResponse(message="If the email exists, a password reset link has been sent")
    
    logger.info(f"[AUTH] User found: {user.name} ({user.email})")
    
    # Generate a secure reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Invalidate any existing reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id
    ).delete()
    
    # Create new reset token
    token_record = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=expires_at
    )
    db.add(token_record)
    db.commit()
    
    logger.info(f"[AUTH] Reset token created, sending email...")
    
    # Send password reset email
    email_sent = send_password_reset_email(
        to_email=user.email,
        reset_token=reset_token,
        user_name=user.name
    )
    
    logger.info(f"[AUTH] Email send result: {email_sent}")
    
    return MessageResponse(message="If the email exists, a password reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a valid token"""
    # Find the token
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update user password
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    user.password_hash = get_password_hash(request.new_password)
    
    # Mark token as used
    token_record.used = True
    
    db.commit()
    
    return MessageResponse(message="Password has been reset successfully")
