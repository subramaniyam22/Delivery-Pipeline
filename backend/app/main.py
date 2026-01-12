from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, users, projects, workflow, artifacts, tasks, defects, config_admin, onboarding, testing, capacity, leave_holiday, sla, client_management
from app.services.config_service import seed_default_configs
from app.db import SessionLocal
from app.models import User, Role
from app.auth import get_password_hash
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def seed_admin_user(db):
    """Seed default admin user if not exists"""
    admin_email = "subramaniyam.webdesigner@gmail.com"
    existing = db.query(User).filter(User.email == admin_email).first()
    if not existing:
        admin = User(
            name="Admin User",
            email=admin_email,
            password_hash=get_password_hash("admin123"),
            role=Role.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        logger.info(f"Admin user created: {admin_email}")
    else:
        logger.info(f"Admin user already exists: {admin_email}")

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
    
    # Seed default configs and admin user
    try:
        db = SessionLocal()
        seed_default_configs(db)
        seed_admin_user(db)
        db.close()
        logger.info("Default configurations seeded")
    except Exception as e:
        logger.error(f"Failed to seed default configs: {e}")


# Register routers
# NOTE: onboarding router must come BEFORE projects router
# because onboarding has /projects/templates and /projects/copy-pricing
# which would otherwise match projects' /{project_id} route and fail UUID validation
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(onboarding.router)  # Must be before projects router
app.include_router(projects.router)
app.include_router(workflow.router)
app.include_router(artifacts.router)
app.include_router(tasks.router)
app.include_router(defects.router)
app.include_router(testing.router)
app.include_router(capacity.router)
app.include_router(leave_holiday.router)
app.include_router(sla.router)
app.include_router(client_management.router)
app.include_router(config_admin.router)


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
