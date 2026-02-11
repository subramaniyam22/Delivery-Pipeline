from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.routers import auth, users, projects, workflow, artifacts, tasks, defects, config_admin, onboarding, testing, capacity, leave_holiday, sla, client_management, project_management, configuration, ai_consultant, cache, analytics, websocket, notifications, webhooks, jobs, preview, sentiment_public, sentiments, metrics, audit_logs
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
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.middleware.request_id import RequestIDMiddleware
from app.middleware.body_limit import BodySizeLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.utils.logging import configure_logging

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

configure_logging(logging.INFO)
logger = logging.getLogger(__name__)
IS_PROD = os.getenv("ENVIRONMENT") == "production"


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


SEED_PASSWORD = "Admin@123"

# All demo users seeded on startup (localhost and Render). Password for all: Admin@123
DEMO_USERS = [
    (Role.ADMIN, "subramaniyam.webdesigner@gmail.com", "Admin User"),
    (Role.CONSULTANT, "subramaniyam@consultant.com", "Subramaniyam Consultant"),
    (Role.CONSULTANT, "jane@consultant.com", "Jane Consultant"),
    (Role.PC, "subramaniyam@pc.com", "Subramaniyam PC"),
    (Role.PC, "john@pc.com", "John PC"),
    (Role.BUILDER, "subramaniyam@builder.com", "Subramaniyam Builder"),
    (Role.BUILDER, "bob@builder.com", "Bob Builder"),
    (Role.TESTER, "subramaniyam@tester.com", "Subramaniyam Tester"),
    (Role.TESTER, "alice@tester.com", "Alice Tester"),
    (Role.MANAGER, "subramaniyam@manager.com", "Subramaniyam Manager"),
    (Role.MANAGER, "alice@manager.com", "Alice Manager"),
    (Role.MANAGER, "subramaniyam@usmanager.com", "Subramaniyam US Manager"),
    (Role.SALES, "subramaniyam@sales.com", "Subramaniyam Sales"),
    (Role.SALES, "alice@sales.com", "Alice Sales"),
]


def seed_admin_user(db):
    """Seed default admin user; create or update password to Admin@123 so login always works."""
    admin_email = "subramaniyam.webdesigner@gmail.com"
    existing = db.query(User).filter(User.email == admin_email).first()
    if not existing:
        admin = User(
            name="Admin User",
            email=admin_email,
            password_hash=get_password_hash(SEED_PASSWORD),
            role=Role.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        logger.info(f"Admin user created: {admin_email}")
    else:
        existing.password_hash = get_password_hash(SEED_PASSWORD)
        existing.is_active = True
        db.commit()
        logger.info(f"Admin user password synced: {admin_email}")


def seed_demo_users(db):
    """Seed all demo users for localhost and Render (password: Admin@123). Create or sync password."""
    for role, email, name in DEMO_USERS:
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            user = User(
                name=name,
                email=email,
                password_hash=get_password_hash(SEED_PASSWORD),
                role=role,
                is_active=True
            )
            db.add(user)
            db.commit()
            logger.info(f"Demo user created: {email} ({role.value})")
        else:
            existing.password_hash = get_password_hash(SEED_PASSWORD)
            existing.role = role
            existing.name = name
            existing.is_active = True
            db.commit()
            logger.info(f"Demo user synced: {email} ({role.value})")


# Create FastAPI app
app = FastAPI(
    title="Delivery Automation Suite",
    description="Production-ready delivery management system with AI agents",
    version="1.0.0"
)

# Add rate limiting state
app.state.limiter = limiter

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

allowed_origins = settings.cors_origins_list
if settings.FRONTEND_URL and settings.FRONTEND_URL not in allowed_origins:
    allowed_origins.append(settings.FRONTEND_URL)

# CORS: allow listed origins + regex for *.onrender.com so preflight OPTIONS get Access-Control-Allow-Origin
cors_regex = settings.CORS_ORIGIN_REGEX
if not cors_regex and "onrender.com" in str(settings.CORS_ORIGINS):
    cors_regex = r"^https://[a-zA-Z0-9-]+\.onrender\.com$"
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=cors_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_UPLOAD_SIZE)
app.add_middleware(SecurityHeadersMiddleware)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Delivery Automation Suite...")
    
    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory created: {settings.UPLOAD_DIR}")
    
    # Seed default configs and admin user
    try:
        db = SessionLocal()
        seed_default_configs(db)
        seed_admin_user(db)
        seed_demo_users(db)
        db.close()

        # Ensure notifications table exists
        try:
            from create_notifications_table import create_table
            create_table()
            logger.info("Notifications table verified/created")
        except Exception as e:
            logger.error(f"Failed to create notifications table: {e}")

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
app.include_router(notifications.router)
app.include_router(webhooks.router)
app.include_router(jobs.router)
app.include_router(preview.router)
app.include_router(sentiment_public.router)
app.include_router(sentiments.router)
app.include_router(audit_logs.router)
app.include_router(metrics.router)

# Serve uploaded files
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Serve generated previews (AI template previews)
generated_preview_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_previews")
os.makedirs(generated_preview_dir, exist_ok=True)
app.mount("/previews", StaticFiles(directory=generated_preview_dir), name="previews")


def _check_migrations() -> bool:
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_cfg_path = os.path.join(current_dir, "alembic.ini")
        alembic_cfg = Config(alembic_cfg_path)
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url_fixed)
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = set(script.get_heads())
        db = SessionLocal()
        current = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        db.close()
        if not current:
            return False
        return current[0] in heads
    except Exception:
        return False


@app.get("/version")
def get_version():
    return {
        "version": os.getenv("RENDER_GIT_COMMIT") or "unknown",
        "build_timestamp": os.getenv("BUILD_TIMESTAMP") or "unknown",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    checks = {"database": False, "redis": False, "migrations": False}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False
    try:
        from app.utils.cache import cache
        if cache.client:
            cache.client.ping()
            checks["redis"] = True
    except Exception:
        checks["redis"] = False
    checks["migrations"] = _check_migrations()
    if all(checks.values()):
        return {"status": "ok", "checks": checks}
    raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})

@app.get("/debug-schema")
def debug_schema(db: Session = Depends(get_db)):
    if IS_PROD:
        logger.warning("Blocked debug endpoint access: /debug-schema")
        raise HTTPException(status_code=404, detail="Not found")
    from sqlalchemy import text
    try:
        result = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'projects'")).fetchall()
        return {"columns": [{row[0]: row[1]} for row in result]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Delivery Automation Suite API",
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
    if IS_PROD:
        logger.warning("Blocked debug endpoint access: /debug-db")
        raise HTTPException(status_code=404, detail="Not found")
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

@app.delete("/debug-projects")
def debug_delete_projects(secret: str):
    if IS_PROD:
        logger.warning("Blocked debug endpoint access: /debug-projects")
        raise HTTPException(status_code=404, detail="Not found")
    if secret != "clean_render_db_now":
        return JSONResponse(status_code=403, content={"error": "Invalid secret"})
        
    from app.db import SessionLocal
    from sqlalchemy import text
    try:
        db = SessionLocal()
        # Use TRUNCATE CASCADE to clean projects and all dependent tables (tasks, logs, etc.)
        # This assumes no Foreign Keys point TO projects from tables we want to keep (like Users).
        # Users -> Projects (FK in Project). So Projects depends on Users. Truncating Projects is fine.
        db.execute(text("TRUNCATE TABLE projects CASCADE"))
        db.commit()
        return {"status": "ok", "message": "All projects and dependencies wiped via TRUNCATE CASCADE."}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}
    finally:
        db.close()
