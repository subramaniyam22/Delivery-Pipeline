"""
Analytics router for metrics and insights.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_active_user
from app.models import User
from app.services.analytics_service import analytics_service
from app.rate_limit import limiter
from typing import Dict, Any

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute
def get_dashboard_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get comprehensive dashboard analytics."""
    return analytics_service.get_dashboard_summary(db)


@router.get("/velocity")
@limiter.limit("20/minute")  # Rate limit: 20 requests per minute
def get_project_velocity(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get project velocity metrics."""
    return analytics_service.get_project_velocity(db, days)


@router.get("/stage-distribution")
@limiter.limit("20/minute")
def get_stage_distribution(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, int]:
    """Get distribution of projects across stages."""
    return analytics_service.get_stage_distribution(db)


@router.get("/team-performance")
@limiter.limit("15/minute")
def get_team_performance(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get team performance metrics."""
    return analytics_service.get_team_performance(db)


@router.get("/sla-compliance")
@limiter.limit("15/minute")
def get_sla_compliance(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get SLA compliance metrics."""
    return analytics_service.get_sla_compliance(db)


@router.get("/bottlenecks")
@limiter.limit("15/minute")
def get_bottleneck_analysis(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get bottleneck analysis."""
    return analytics_service.get_bottleneck_analysis(db)


@router.get("/resource-utilization")
@limiter.limit("15/minute")
def get_resource_utilization(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get resource utilization metrics."""
    return analytics_service.get_resource_utilization(db)
