from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, users, projects, workflow, artifacts, tasks, defects, config_admin, onboarding, testing, capacity, leave_holiday, sla, client_management, project_management, configuration, ai_consultant
from app.services.config_service import seed_default_configs
from app.db import SessionLocal
from app.models import User, Role
from app.auth import get_password_hash
import os
import logging
from alembic import command
from alembic.config import Config
from alembic.config import Config
# Trigger reload 2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run Alembic migrations on startup"""
    try:
        logger.info("Running DB migrations...")
        
        # Point to alembic.ini relative to this file
        # backend/app/main.py -> backend/
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_cfg_path = os.path.join(current_dir, "alembic.ini")
        
        # Create Alembic Config object
        alembic_cfg = Config(alembic_cfg_path)
        
        # Override sqlalchemy.url with the fixed production URL
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url_fixed)
        
        # Run upgrade head
        command.upgrade(alembic_cfg, "head")
        logger.info("DB migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run DB migrations: {e}")
        # We don't raise here to allow app to start even if migration fails (though risky)
        # But for 'features_json' missing, app might fail later anyway.


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

def seed_manager_users(db):
    """Seed default manager users if not exist"""
    managers = [
        {"email": "subramaniyam@manager.com", "name": "Subramaniyam Manager"},
        {"email": "alice@manager.com", "name": "Alice Manager"}
    ]
    
    for mgr_data in managers:
        existing = db.query(User).filter(User.email == mgr_data["email"]).first()
        if not existing:
            manager = User(
                name=mgr_data["name"],
                email=mgr_data["email"],
                password_hash=get_password_hash("Admin@123"),
                role=Role.MANAGER,
                is_active=True
            )
            db.add(manager)
            db.commit()
            logger.info(f"Manager user created: {mgr_data['email']}")
        else:
            logger.info(f"Manager user already exists: {mgr_data['email']}")

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
    
    # 1. Run Migrations
    run_migrations()
    
    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory created: {settings.UPLOAD_DIR}")
    
    # Seed default configs and admin user
    try:
        db = SessionLocal()
        seed_default_configs(db)
        seed_admin_user(db)
        seed_manager_users(db)
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
app.include_router(project_management.router)
app.include_router(config_admin.router)
app.include_router(configuration.router)
app.include_router(ai_consultant.router)

# Serve uploaded files
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


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
