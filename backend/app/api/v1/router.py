"""
API v1 router - versioned API endpoints.
"""
from fastapi import APIRouter
from app.routers import (
    auth,
    users,
    projects,
    tasks,
    defects,
    artifacts,
    onboarding,
    workflow,
    cache,
    websocket
)

# Create v1 API router
api_v1_router = APIRouter(prefix="/api/v1")

# Include all routers
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(projects.router)
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(defects.router)
api_v1_router.include_router(artifacts.router)
api_v1_router.include_router(onboarding.router)
api_v1_router.include_router(workflow.router)
api_v1_router.include_router(cache.router)
api_v1_router.include_router(websocket.router)
