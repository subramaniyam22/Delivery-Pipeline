from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.routers import auth, users, projects, workflow, artifacts, tasks, defects, config_admin, onboarding, testing, capacity, leave_holiday, sla, client_management, project_management, configuration, ai_consultant, cache, analytics, websocket
from app.services.config_service import seed_default_configs
from app.db import SessionLocal
from app.models import User, Role
from app.auth import get_password_hash
from app.deps import get_db
from sqlalchemy.orm import Session

# Import error handling and rate limiting
from app.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from app.rate_limit import limiter, rate_limit_exceeded_handler

import os
import logging
from alembic import command
from alembic.config import Config

# Sentry integration (optional)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    
    # Only initialize if DSN is provided
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            environment=os.getenv("ENVIRONMENT", "development"),
        )
        logging.info("Sentry error tracking initialized")
except ImportError:
    logging.warning("Sentry SDK not installed, skipping error tracking")

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
                password_hash=get_password_hash("manager123"),
                role=Role.MANAGER,
                is_active=True
            )
            db.add(manager)
            db.commit()
            logger.info(f"Manager user created: {mgr_data['email']}")


# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Delivery Pipeline",
    description="Production-ready delivery management system with AI agents",
    version="1.0.0"
)

# Add rate limiting state
app.state.limiter = limiter

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
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
        seed_manager_users(db)
        db.close()
        logger.info("Default configurations seeded")
    except Exception as e:
        logger.error(f"Failed to seed default configs: {e}")


# Register routers
# NOTE: onboarding router must come BEFORE projects router
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
app.include_router(cache.router)
app.include_router(analytics.router)
app.include_router(websocket.router)

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
async def health_check(db: Session = Depends(get_db)):
    """Enhanced health check with dependency verification"""
    from sqlalchemy import text
    health_status = {"status": "ok", "checks": {}}
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = "error"
        health_status["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")
    
    # Check Redis
    try:
        from app.utils.cache import cache
        if cache.client:
            cache.client.ping()
            health_status["checks"]["redis"] = "ok"
        else:
            health_status["checks"]["redis"] = "not_configured"
    except Exception as e:
        health_status["checks"]["redis"] = "error"
        health_status["status"] = "degraded"
        logger.error(f"Redis health check failed: {e}")
    
    return health_status

@app.get("/debug-db")
def debug_database():
    from app.models import Project
    from app.db import SessionLocal
    try:
        db = SessionLocal()
        # Try simple query
        count = db.query(Project).count()
        # Try fetching one to check columns
        first = db.query(Project).first()
        data = {}
        if first:
            data = {
                "id": str(first.id), 
                "title": first.title,
                # Access potentially problematic columns to trigger load
                "manager_user_id": str(first.manager_user_id) if first.manager_user_id else None
            }
        return {"status": "ok", "count": count, "first_project": data}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}
    finally:
        db.close()
