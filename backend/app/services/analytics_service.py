"""
Analytics service for project metrics and insights.
"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import Project, ProjectStatus, Stage, User, Role, ProjectTask, TaskStatus
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for calculating project analytics and metrics."""
    
    @staticmethod
    def get_project_velocity(db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Calculate project velocity (projects completed per time period).
        
        Args:
            db: Database session
            days: Number of days to analyze
        
        Returns:
            Velocity metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Count completed projects
        completed = db.query(Project).filter(
            and_(
                Project.status == ProjectStatus.COMPLETED,
                Project.updated_at >= cutoff_date
            )
        ).count()
        
        # Count in-progress projects
        in_progress = db.query(Project).filter(
            Project.status == ProjectStatus.ACTIVE
        ).count()
        
        # Calculate velocity
        velocity = completed / days if days > 0 else 0
        
        return {
            "period_days": days,
            "completed_projects": completed,
            "in_progress_projects": in_progress,
            "velocity_per_day": round(velocity, 2),
            "projected_monthly": round(velocity * 30, 1)
        }
    
    @staticmethod
    def get_stage_distribution(db: Session) -> Dict[str, int]:
        """Get distribution of projects across stages."""
        results = db.query(
            Project.current_stage,
            func.count(Project.id)
        ).filter(
            Project.status != ProjectStatus.COMPLETED
        ).group_by(Project.current_stage).all()
        
        return {stage.value: count for stage, count in results}
    
    @staticmethod
    def get_team_performance(db: Session) -> List[Dict[str, Any]]:
        """Get performance metrics by team member."""
        # Projects by sales rep
        sales_stats = db.query(
            User.id,
            User.name,
            func.count(Project.id).label('project_count')
        ).join(
            Project, Project.sales_user_id == User.id
        ).filter(
            User.role == Role.SALES
        ).group_by(User.id, User.name).all()
        
        team_performance = []
        for user_id, name, count in sales_stats:
            team_performance.append({
                "user_id": str(user_id),
                "name": name,
                "role": "SALES",
                "project_count": count
            })
        
        return team_performance
    
    @staticmethod
    def get_sla_compliance(db: Session) -> Dict[str, Any]:
        """Calculate SLA compliance metrics."""
        total_projects = db.query(Project).filter(
            Project.status != ProjectStatus.DRAFT
        ).count()
        
        delayed_projects = db.query(Project).filter(
            Project.is_delayed == True
        ).count()
        
        on_time = total_projects - delayed_projects
        compliance_rate = (on_time / total_projects * 100) if total_projects > 0 else 100
        
        return {
            "total_projects": total_projects,
            "on_time": on_time,
            "delayed": delayed_projects,
            "compliance_rate": round(compliance_rate, 2)
        }
    
    @staticmethod
    def get_bottleneck_analysis(db: Session) -> List[Dict[str, Any]]:
        """Identify bottlenecks in the pipeline."""
        # Average time in each stage
        stage_times = []
        
        for stage in Stage:
            # Count projects in this stage
            count = db.query(Project).filter(
                and_(
                    Project.current_stage == stage,
                    Project.status == ProjectStatus.ACTIVE
                )
            ).count()
            
            if count > 0:
                stage_times.append({
                    "stage": stage.value,
                    "project_count": count,
                    "is_bottleneck": count > 5  # Simple threshold
                })
        
        return sorted(stage_times, key=lambda x: x['project_count'], reverse=True)
    
    @staticmethod
    def get_resource_utilization(db: Session) -> Dict[str, Any]:
        """Calculate resource utilization metrics."""
        # Count active users by role
        role_counts = db.query(
            User.role,
            func.count(User.id)
        ).filter(
            User.is_active == True
        ).group_by(User.role).all()
        
        utilization = {}
        for role, count in role_counts:
            # Count projects assigned to this role
            if role == Role.SALES:
                assigned = db.query(Project).filter(
                    Project.sales_user_id.isnot(None)
                ).count()
            elif role == Role.MANAGER:
                assigned = db.query(Project).filter(
                    Project.manager_user_id.isnot(None)
                ).count()
            else:
                assigned = 0
            
            utilization[role.value] = {
                "total_users": count,
                "assigned_projects": assigned,
                "avg_per_user": round(assigned / count, 1) if count > 0 else 0
            }
        
        return utilization
    
    @staticmethod
    def get_dashboard_summary(db: Session) -> Dict[str, Any]:
        """Get comprehensive dashboard summary."""
        return {
            "velocity": AnalyticsService.get_project_velocity(db, days=30),
            "stage_distribution": AnalyticsService.get_stage_distribution(db),
            "sla_compliance": AnalyticsService.get_sla_compliance(db),
            "bottlenecks": AnalyticsService.get_bottleneck_analysis(db),
            "resource_utilization": AnalyticsService.get_resource_utilization(db),
            "generated_at": datetime.utcnow().isoformat()
        }


# Global analytics service instance
analytics_service = AnalyticsService()
