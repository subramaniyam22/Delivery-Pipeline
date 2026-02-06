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
    
    # Upload - Use absolute path derived from project root
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # S3 Storage (optional)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    S3_PUBLIC_BASE_URL: Optional[str] = None

    @property
    def S3_BUCKET(self) -> Optional[str]:
        return self.AWS_S3_BUCKET

    @property
    def S3_BUCKET_NAME(self) -> Optional[str]:
        return self.AWS_S3_BUCKET
    
    # Redis (for rate limiting and caching)
    REDIS_URL: str = "redis://localhost:6379"
    
    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None
    
    # CORS - parse from environment variable
    CORS_ORIGINS: str = "http://localhost:3000,http://frontend:3000,https://delivery-frontend-60cf.onrender.com"
    
    # Frontend URL for client links
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Email (Resend)
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "Delivery Management <noreply@resend.dev>"
    APP_NAME: str = "Delivery Management"
    
    # Error Tracking (Sentry)
    SENTRY_DSN: Optional[str] = None
    ENVIRONMENT: str = "development"
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
