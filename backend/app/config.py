from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://delivery_user:delivery_pass@localhost:5432/delivery_db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 6
    
    # Upload
    UPLOAD_DIR: str = "/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://frontend:3000"]
    
    # Frontend URL for client links
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
