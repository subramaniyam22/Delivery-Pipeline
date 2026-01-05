from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, users, projects, workflow, artifacts, tasks, defects, config_admin, onboarding
from app.services.config_service import seed_default_configs
from app.db import SessionLocal
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Delivery Pipeline",
    description="Production-ready MVP with FastAPI + LangGraph + Next.js",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Multi-Agent Delivery Pipeline...")
    
    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory created: {settings.UPLOAD_DIR}")
    
    # Seed default configs
    try:
        db = SessionLocal()
        seed_default_configs(db)
        db.close()
        logger.info("Default configurations seeded")
    except Exception as e:
        logger.error(f"Failed to seed default configs: {e}")


# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(workflow.router)
app.include_router(artifacts.router)
app.include_router(tasks.router)
app.include_router(defects.router)
app.include_router(config_admin.router)
app.include_router(onboarding.router)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Multi-Agent Delivery Pipeline API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
