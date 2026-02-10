from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database - Handle Render's postgres:// URL format
    DATABASE_URL: str = "postgresql://delivery_user:delivery_pass@localhost:5432/delivery_db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 6

    # Token signing (rotation support)
    SECRET_KEY_CURRENT: Optional[str] = None
    SECRET_KEY_PREVIOUS: Optional[str] = None
    
    # Upload - Use absolute path derived from project root
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Storage backend
    STORAGE_BACKEND: str = "local"  # local | s3
    STORAGE_PUBLIC_BASE_URL: Optional[str] = None

    # S3 Storage (optional)
    S3_ENDPOINT_URL: Optional[str] = None
    S3_BUCKET: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: Optional[str] = None
    S3_PUBLIC_BASE_URL: Optional[str] = None

    # Backwards compatibility
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    
    # Redis (for rate limiting and caching)
    REDIS_URL: str = "redis://localhost:6379"
    
    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None
    AI_MODE: str = "full"  # disabled | basic | full
    
    # CORS - parse from environment variable (comma-separated). Use CORS_ORIGIN_REGEX for patterns (e.g. *.onrender.com).
    CORS_ORIGINS: str = "http://localhost:3000"
    CORS_ORIGIN_REGEX: Optional[str] = None  # e.g. "^https://[a-zA-Z0-9-]+\\.onrender\\.com$"

    # Frontend URL for client links
    FRONTEND_URL: str = "http://localhost:3000"

    # API URL for preview links
    BACKEND_URL: Optional[str] = None
    
    # Email (Resend)
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "Delivery Automation Suite <noreply@resend.dev>"
    APP_NAME: str = "Delivery Automation Suite"

    # SMTP (Completion emails)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    FROM_EMAIL: Optional[str] = None

    # Webhooks
    CHAT_LOG_WEBHOOK_URL: Optional[str] = None
    CHAT_LOG_WEBHOOK_SECRET: Optional[str] = None
    
    # Error Tracking (Sentry)
    SENTRY_DSN: Optional[str] = None
    ENVIRONMENT: str = "development"

    # Sentiment tokens
    SENTIMENT_TOKEN_TTL_HOURS: int = 168
    PREVIEW_TOKEN_TTL_HOURS: int = 72

    # Rate limits
    RATE_LIMIT_AI_PER_MINUTE: int = 30
    RATE_LIMIT_PUBLIC_PER_MINUTE: int = 60
    
    @property
    def database_url_fixed(self) -> str:
        """Fix Render's postgres:// to postgresql:// for SQLAlchemy"""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    
    @property
    def cors_origins_list(self) -> list:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def token_signing_keys(self) -> list:
        keys = []
        if self.SECRET_KEY_CURRENT:
            keys.append(self.SECRET_KEY_CURRENT)
        if self.SECRET_KEY_PREVIOUS:
            keys.append(self.SECRET_KEY_PREVIOUS)
        if not keys:
            keys.append(self.SECRET_KEY)
        return keys
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
