"""
Capacity Management Service
Handles capacity tracking, allocation, and AI-powered suggestions
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import statistics

from app.models import (
    User, Role, Region, Project, Stage,
    CapacityConfig, UserDailyCapacity, ProjectWorkload,
    CapacityAllocation, CapacitySuggestion, CapacityHistory,
    CapacityManualInput, DEFAULT_STAGE_WORKLOAD,
    UserLeave, LeaveStatus, RegionHoliday, CompanyHoliday
)


class CapacityService:
    """Service for managing team capacity"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Configuration ====================
    
    def get_capacity_config(self, role: Role, region: Optional[Region] = None) -> CapacityConfig:
        """Get capacity configuration for a role/region combination"""
        # First try exact match
        config = self.db.query(CapacityConfig).filter(
            CapacityConfig.role == role,
            CapacityConfig.region == region,
            CapacityConfig.is_active == True
        ).first()
        
        if config:
            return config
        
        # Fall back to role-only config (no region specified)
        config = self.db.query(CapacityConfig).filter(
            CapacityConfig.role == role,
            CapacityConfig.region == None,
            CapacityConfig.is_active == True
        ).first()
        
        if config:
            return config
        
        # Create default config if none exists
        return self._create_default_config(role, region)
    
    def _create_default_config(self, role: Role, region: Optional[Region]) -> CapacityConfig:
        """Create default capacity config"""
        config = CapacityConfig(
            role=role,
            region=region,
            daily_hours=6.8,
            weekly_hours=34.0,
            buffer_percentage=10.0,
            is_active=True,
            created_at=datetime.utcnow()
        )
        self.db.add(config)
        self.db.commit()
        return config
    
    def update_capacity_config(self, config_id: UUID, updates: Dict[str, Any]) -> CapacityConfig:
        """Update capacity configuration"""
        config = self.db.query(CapacityConfig).filter(CapacityConfig.id == config_id).first()
        if not config:
            raise ValueError("Configuration not found")
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.updated_at = datetime.utcnow()
        self.db.commit()
        return config
    
    def list_capacity_configs(self) -> List[CapacityConfig]:
        """List all active capacity configurations"""
        return self.db.query(CapacityConfig).filter(
            CapacityConfig.is_active == True
        ).all()
    
    # ==================== Leave & Holiday Management ====================
    
    def is_user_on_leave(self, user_id: UUID, target_date: date) -> tuple[bool, Optional[UserLeave]]:
        """Check if user is on approved leave for a specific date"""
        leave = self.db.query(UserLeave).filter(
            UserLeave.user_id == user_id,
            UserLeave.status == LeaveStatus.APPROVED,
            UserLeave.start_date <= target_date,
            UserLeave.end_date >= target_date
        ).first()
        
        if leave:
            return True, leave
        return False, None
    
    def get_user_leaves(self, user_id: UUID, start_date: date, end_date: date) -> List[UserLeave]:
        """Get all approved leaves for a user in date range"""
        return self.db.query(UserLeave).filter(
            UserLeave.user_id == user_id,
            UserLeave.status == LeaveStatus.APPROVED,
            or_(
                and_(UserLeave.start_date >= start_date, UserLeave.start_date <= end_date),
                and_(UserLeave.end_date >= start_date, UserLeave.end_date <= end_date),
                and_(UserLeave.start_date <= start_date, UserLeave.end_date >= end_date)
            )
        ).all()
    
    def is_region_holiday(self, region: Region, target_date: date) -> tuple[bool, Optional[RegionHoliday]]:
        """Check if date is a region-specific holiday"""
        holiday = self.db.query(RegionHoliday).filter(
            RegionHoliday.region == region,
            RegionHoliday.date == target_date,
            RegionHoliday.is_optional == False
        ).first()
        
        if holiday:
            return True, holiday
        return False, None
    
    def is_company_holiday(self, target_date: date) -> tuple[bool, Optional[CompanyHoliday]]:
        """Check if date is a company-wide holiday"""
        holiday = self.db.query(CompanyHoliday).filter(
            CompanyHoliday.date == target_date
        ).first()
        
        if holiday:
            return True, holiday
        return False, None
    
    def get_holidays_for_region(self, region: Region, start_date: date, end_date: date) -> List[Dict]:
        """Get all holidays (company + region) for a date range"""
        holidays = []
        
        # Company holidays
        company_holidays = self.db.query(CompanyHoliday).filter(
            CompanyHoliday.date >= start_date,
            CompanyHoliday.date <= end_date
        ).all()
        for h in company_holidays:
            holidays.append({
                "date": h.date.isoformat(),
                "name": h.name,
                "type": "company",
                "is_optional": False
            })
        
        # Region holidays
        region_holidays = self.db.query(RegionHoliday).filter(
            RegionHoliday.region == region,
            RegionHoliday.date >= start_date,
            RegionHoliday.date <= end_date
        ).all()
        for h in region_holidays:
            holidays.append({
                "date": h.date.isoformat(),
                "name": h.name,
                "type": "region",
                "is_optional": h.is_optional
            })
        
        return sorted(holidays, key=lambda x: x["date"])
    
    def get_user_unavailable_dates(self, user_id: UUID, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get all unavailable dates for a user (leaves + holidays)"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        unavailable = {
            "leaves": [],
            "holidays": [],
            "total_unavailable_days": 0
        }
        
        # Get leaves
        leaves = self.get_user_leaves(user_id, start_date, end_date)
        for leave in leaves:
            leave_start = max(leave.start_date, start_date)
            leave_end = min(leave.end_date, end_date)
            days = (leave_end - leave_start).days + 1
            
            # Count only work days (weekdays)
            work_days = sum(1 for i in range(days) 
                          if (leave_start + timedelta(days=i)).weekday() < 5)
            
            unavailable["leaves"].append({
                "type": leave.leave_type.value,
                "start_date": leave.start_date.isoformat(),
                "end_date": leave.end_date.isoformat(),
                "days": work_days,
                "partial": leave.partial_day,
                "hours_off": leave.hours_off if leave.partial_day else None
            })
            unavailable["total_unavailable_days"] += work_days
        
        # Get holidays
        if user.region:
            holidays = self.get_holidays_for_region(user.region, start_date, end_date)
            for h in holidays:
                holiday_date = date.fromisoformat(h["date"])
                if holiday_date.weekday() < 5 and not h["is_optional"]:
                    unavailable["holidays"].append(h)
                    unavailable["total_unavailable_days"] += 1
        
        return unavailable
    
    # ==================== User Capacity ====================
    
    def get_user_daily_capacity(self, user_id: UUID, target_date: date) -> UserDailyCapacity:
        """Get or create daily capacity record for a user (accounting for leaves/holidays)"""
        capacity = self.db.query(UserDailyCapacity).filter(
            UserDailyCapacity.user_id == user_id,
            UserDailyCapacity.date == target_date
        ).first()
        
        if capacity:
            return capacity
        
        # Create new capacity record based on user's role/region config
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        config = self.get_capacity_config(user.role, user.region)
        daily_hours = config.daily_hours
        is_available = True
        unavailability_reason = None
        
        # Check if user is on leave
        on_leave, leave = self.is_user_on_leave(user_id, target_date)
        if on_leave:
            if leave.partial_day and leave.hours_off:
                # Partial day leave - reduce capacity
                daily_hours = max(0, daily_hours - leave.hours_off)
            else:
                # Full day leave - no capacity
                daily_hours = 0
                is_available = False
                unavailability_reason = f"On {leave.leave_type.value} leave"
        
        # Check company holiday
        if is_available:
            is_company_holiday, company_holiday = self.is_company_holiday(target_date)
            if is_company_holiday:
                daily_hours = 0
                is_available = False
                unavailability_reason = f"Company Holiday: {company_holiday.name}"
        
        # Check region holiday
        if is_available and user.region:
            is_regional_holiday, regional_holiday = self.is_region_holiday(user.region, target_date)
            if is_regional_holiday:
                daily_hours = 0
                is_available = False
                unavailability_reason = f"Regional Holiday: {regional_holiday.name}"
        
        capacity = UserDailyCapacity(
            user_id=user_id,
            date=target_date,
            total_hours=daily_hours,
            allocated_hours=0.0,
            is_available=is_available,
            unavailability_reason=unavailability_reason,
            created_at=datetime.utcnow()
        )
        self.db.add(capacity)
        self.db.commit()
        return capacity
    
    def get_user_capacity_range(self, user_id: UUID, start_date: date, end_date: date) -> List[UserDailyCapacity]:
        """Get user capacity for a date range"""
        capacities = []
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends (assuming 5-day work week)
            if current_date.weekday() < 5:
                capacities.append(self.get_user_daily_capacity(user_id, current_date))
            current_date += timedelta(days=1)
        return capacities
    
    def get_user_capacity_summary(self, user_id: UUID, weeks: int = 2) -> Dict[str, Any]:
        """Get capacity summary for a user over specified weeks"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        today = date.today()
        start_date = today
        end_date = today + timedelta(weeks=weeks)
        
        capacities = self.get_user_capacity_range(user_id, start_date, end_date)
        
        total_hours = sum(c.total_hours for c in capacities)
        allocated_hours = sum(c.allocated_hours for c in capacities)
        remaining_hours = sum(c.remaining_hours for c in capacities)
        
        # Get active project count
        active_projects = self.db.query(CapacityAllocation).filter(
            CapacityAllocation.user_id == user_id,
            CapacityAllocation.date >= start_date,
            CapacityAllocation.date <= end_date
        ).distinct(CapacityAllocation.project_id).count()
        
        return {
            "user_id": str(user_id),
            "user_name": user.name,
            "role": user.role.value,
            "region": user.region.value if user.region else None,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_hours": round(total_hours, 1),
            "allocated_hours": round(allocated_hours, 1),
            "remaining_hours": round(remaining_hours, 1),
            "utilization_percentage": round((allocated_hours / total_hours * 100) if total_hours > 0 else 0, 1),
            "active_projects": active_projects,
            "daily_capacities": [
                {
                    "date": c.date.isoformat(),
                    "total": c.total_hours,
                    "allocated": c.allocated_hours,
                    "remaining": c.remaining_hours,
                    "is_available": c.is_available
                }
                for c in capacities
            ]
        }
    
    def allocate_capacity(
        self, 
        user_id: UUID, 
        project_id: UUID, 
        target_date: date, 
        hours: float,
        workload_id: Optional[UUID] = None
    ) -> CapacityAllocation:
        """Allocate capacity hours to a project"""
        # Get/create daily capacity
        daily_capacity = self.get_user_daily_capacity(user_id, target_date)
        
        # Check if enough capacity available
        if daily_capacity.remaining_hours < hours:
            raise ValueError(
                f"Insufficient capacity. Available: {daily_capacity.remaining_hours}h, "
                f"Requested: {hours}h"
            )
        
        # Create allocation
        allocation = CapacityAllocation(
            user_id=user_id,
            project_id=project_id,
            workload_id=workload_id,
            date=target_date,
            allocated_hours=hours,
            created_at=datetime.utcnow()
        )
        self.db.add(allocation)
        
        # Update daily capacity
        daily_capacity.allocated_hours += hours
        daily_capacity.updated_at = datetime.utcnow()
        
        self.db.commit()
        return allocation
    
    # ==================== Available Users ====================
    
    def get_available_users_by_role(
        self, 
        role: Role, 
        start_date: date, 
        end_date: date,
        min_hours: float = 0
    ) -> List[Dict[str, Any]]:
        """Get users with available capacity for a role"""
        users = self.db.query(User).filter(
            User.role == role,
            User.is_active == True,
            User.is_archived == False
        ).all()
        
        result = []
        for user in users:
            summary = self.get_user_capacity_summary(user.id, weeks=2)
            
            # Check if user has minimum required hours
            if summary["remaining_hours"] >= min_hours:
                result.append({
                    **summary,
                    "is_recommended": summary["utilization_percentage"] < 80,
                    "capacity_status": self._get_capacity_status(summary["utilization_percentage"])
                })
        
        # Sort by remaining hours (most available first)
        result.sort(key=lambda x: x["remaining_hours"], reverse=True)
        return result
    
    def _get_capacity_status(self, utilization: float) -> str:
        """Get capacity status based on utilization"""
        if utilization < 50:
            return "LOW"
        elif utilization < 70:
            return "MODERATE"
        elif utilization < 85:
            return "HIGH"
        else:
            return "CRITICAL"
    
    # ==================== Project Workload ====================
    
    def create_project_workload(
        self,
        project_id: UUID,
        stage: Stage,
        role: Role,
        estimated_hours: Optional[float] = None,
        priority_score: float = 1.0,
        complexity_factor: float = 1.0
    ) -> ProjectWorkload:
        """Create workload estimate for a project stage"""
        # Use default if not specified
        if estimated_hours is None:
            stage_defaults = DEFAULT_STAGE_WORKLOAD.get(stage, {})
            estimated_hours = stage_defaults.get(role, 8.0)  # Default 8 hours
        
        workload = ProjectWorkload(
            project_id=project_id,
            stage=stage,
            role=role,
            estimated_hours=estimated_hours * complexity_factor,
            priority_score=priority_score,
            complexity_factor=complexity_factor,
            created_at=datetime.utcnow()
        )
        self.db.add(workload)
        self.db.commit()
        return workload
    
    def get_project_workloads(self, project_id: UUID) -> List[ProjectWorkload]:
        """Get all workloads for a project"""
        return self.db.query(ProjectWorkload).filter(
            ProjectWorkload.project_id == project_id
        ).all()
    
    def estimate_project_workload(self, project: Project) -> Dict[str, Any]:
        """Estimate total workload for a project"""
        workloads = {}
        total_hours = 0
        
        for stage in Stage:
            stage_defaults = DEFAULT_STAGE_WORKLOAD.get(stage, {})
            for role, hours in stage_defaults.items():
                role_key = role.value
                if role_key not in workloads:
                    workloads[role_key] = 0
                workloads[role_key] += hours
                total_hours += hours
        
        return {
            "project_id": str(project.id),
            "total_hours": total_hours,
            "by_role": workloads,
            "by_stage": {
                stage.value: sum(hours for hours in DEFAULT_STAGE_WORKLOAD.get(stage, {}).values())
                for stage in Stage
            }
        }


class CapacitySuggestionService:
    """AI-powered capacity suggestion service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.capacity_service = CapacityService(db)
    
    def generate_assignment_suggestions(
        self, 
        project_id: UUID, 
        role: Role
    ) -> Dict[str, Any]:
        """Generate AI suggestions for team assignment"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("Project not found")
        
        # Get available users
        today = date.today()
        end_date = today + timedelta(weeks=2)
        available_users = self.capacity_service.get_available_users_by_role(
            role, today, end_date
        )
        
        # Get workload estimate
        workload_estimate = self.capacity_service.estimate_project_workload(project)
        required_hours = workload_estimate["by_role"].get(role.value, 8.0)
        
        # Get historical data for learning
        historical_performance = self._get_historical_performance(role)
        
        suggestions = []
        capacity_crunch = len(available_users) == 0 or all(
            u["remaining_hours"] < required_hours for u in available_users
        )
        
        if capacity_crunch:
            # Generate capacity crunch suggestions
            suggestions.append(self._generate_crunch_suggestion(
                project, role, available_users, required_hours
            ))
        else:
            # Rank and suggest users
            ranked_users = self._rank_users_for_assignment(
                available_users, required_hours, historical_performance
            )
            
            for i, user in enumerate(ranked_users[:3]):  # Top 3 suggestions
                suggestion = self._create_assignment_suggestion(
                    project, role, user, required_hours, i + 1, historical_performance
                )
                suggestions.append(suggestion)
        
        return {
            "project_id": str(project_id),
            "project_title": project.title,
            "role": role.value,
            "required_hours": required_hours,
            "capacity_crunch": capacity_crunch,
            "suggestions": suggestions,
            "available_users_count": len(available_users),
            "total_available_hours": sum(u["remaining_hours"] for u in available_users)
        }
    
    def _rank_users_for_assignment(
        self,
        users: List[Dict],
        required_hours: float,
        historical_performance: Dict
    ) -> List[Dict]:
        """Rank users based on multiple factors including leaves/holidays"""
        today = date.today()
        end_date = today + timedelta(weeks=2)
        
        for user in users:
            score = 0.0
            user_id = UUID(user["user_id"])
            
            # Get unavailability info (leaves + holidays)
            try:
                unavailable = self.capacity_service.get_user_unavailable_dates(
                    user_id, today, end_date
                )
                leave_days = unavailable["total_unavailable_days"]
                upcoming_leaves = unavailable["leaves"]
                upcoming_holidays = unavailable["holidays"]
            except:
                leave_days = 0
                upcoming_leaves = []
                upcoming_holidays = []
            
            # Add unavailability info to user dict
            user["upcoming_leave_days"] = leave_days
            user["upcoming_leaves"] = upcoming_leaves
            user["upcoming_holidays"] = upcoming_holidays
            
            # Factor 1: Available capacity (35% weight)
            if user["remaining_hours"] >= required_hours:
                capacity_score = min(user["remaining_hours"] / (required_hours * 2), 1.0)
            else:
                capacity_score = user["remaining_hours"] / required_hours
            score += capacity_score * 35
            
            # Factor 2: Utilization balance (25% weight) - prefer moderately utilized
            utilization = user["utilization_percentage"]
            if 50 <= utilization <= 70:
                score += 25
            elif 30 <= utilization < 50 or 70 < utilization <= 80:
                score += 17
            elif utilization < 30 or utilization > 80:
                score += 8
            
            # Factor 3: Availability stability (20% weight) - penalize upcoming leaves
            # Max 10 work days in 2 weeks, so leave_days/10 gives fraction unavailable
            availability_stability = max(0, 1 - (leave_days / 10))
            score += availability_stability * 20
            
            # Factor 4: Historical efficiency (20% weight)
            user_id_str = user["user_id"]
            if user_id_str in historical_performance:
                efficiency = historical_performance[user_id_str].get("efficiency_score", 1.0)
                score += min(efficiency, 1.2) * 16.67
            else:
                score += 16  # Default for new users
            
            # Calculate match percentage (0-100)
            user["assignment_score"] = round(score, 1)
            user["match_percentage"] = round(min(score, 100), 0)
        
        return sorted(users, key=lambda x: x["assignment_score"], reverse=True)
    
    def _create_assignment_suggestion(
        self,
        project: Project,
        role: Role,
        user: Dict,
        required_hours: float,
        rank: int,
        historical_performance: Dict
    ) -> Dict:
        """Create an assignment suggestion with leave/holiday awareness"""
        confidence = min(0.95, 0.5 + (user["assignment_score"] / 200))
        
        suggestion_text = f"Recommend assigning {user['user_name']} "
        if user["remaining_hours"] >= required_hours:
            suggestion_text += f"with {user['remaining_hours']:.1f}h available capacity. "
        else:
            suggestion_text += f"(partial availability: {user['remaining_hours']:.1f}h). "
        
        suggestion_text += f"Current utilization: {user['utilization_percentage']}%. "
        
        # Add leave warning if applicable
        leave_days = user.get("upcoming_leave_days", 0)
        if leave_days > 0:
            suggestion_text += f"⚠️ {leave_days} day(s) leave/holiday in next 2 weeks. "
        
        if user.get("is_recommended"):
            suggestion_text += "✓ Recommended based on balanced workload."
        
        # Save suggestion to database
        suggestion_record = CapacitySuggestion(
            project_id=project.id,
            role=role,
            suggested_user_id=UUID(user["user_id"]),
            suggestion_type="assignment",
            suggestion_text=suggestion_text,
            confidence_score=confidence,
            factors_json={
                "remaining_hours": user["remaining_hours"],
                "utilization": user["utilization_percentage"],
                "assignment_score": user["assignment_score"],
                "upcoming_leave_days": leave_days,
                "rank": rank
            },
            created_at=datetime.utcnow()
        )
        self.db.add(suggestion_record)
        self.db.commit()
        
        return {
            "id": str(suggestion_record.id),
            "rank": rank,
            "user_id": user["user_id"],
            "user_name": user["user_name"],
            "region": user["region"],
            "suggestion_text": suggestion_text,
            "confidence_score": round(confidence, 2),
            "remaining_hours": user["remaining_hours"],
            "utilization_percentage": user["utilization_percentage"],
            "capacity_status": user["capacity_status"],
            "assignment_score": user["assignment_score"],
            "match_percentage": user.get("match_percentage", 85),
            "upcoming_leave_days": leave_days,
            "upcoming_leaves": user.get("upcoming_leaves", []),
            "upcoming_holidays": user.get("upcoming_holidays", [])
        }
    
    def _generate_crunch_suggestion(
        self,
        project: Project,
        role: Role,
        available_users: List[Dict],
        required_hours: float
    ) -> Dict:
        """Generate suggestions for capacity crunch scenarios"""
        suggestions_text = []
        actions = []
        
        total_available = sum(u["remaining_hours"] for u in available_users)
        shortage = required_hours - total_available
        
        # Suggestion 1: Split work
        if len(available_users) > 1:
            suggestions_text.append(
                f"Consider splitting the workload across multiple {role.value}s. "
                f"Total available: {total_available:.1f}h across {len(available_users)} team members."
            )
            actions.append({
                "type": "split_workload",
                "description": f"Distribute {required_hours}h across {len(available_users)} team members"
            })
        
        # Suggestion 2: Extend timeline
        suggestions_text.append(
            f"Extend project timeline to accommodate capacity constraints. "
            f"Current shortage: {shortage:.1f}h."
        )
        actions.append({
            "type": "extend_timeline",
            "description": f"Add {max(1, int(shortage / 6.8))} more days to timeline"
        })
        
        # Suggestion 3: Hire/reassign
        if shortage > 10:
            suggestions_text.append(
                f"Consider temporary resource augmentation or cross-training. "
                f"Significant capacity gap of {shortage:.1f}h detected."
            )
            actions.append({
                "type": "resource_augmentation",
                "description": "Consider hiring contractors or cross-training team members"
            })
        
        # Suggestion 4: Prioritize
        suggestions_text.append(
            "Review project priority and consider rescheduling lower-priority work."
        )
        actions.append({
            "type": "reprioritize",
            "description": "Review and adjust project priorities"
        })
        
        # Save crunch suggestion
        suggestion_record = CapacitySuggestion(
            project_id=project.id,
            role=role,
            suggestion_type="capacity_crunch",
            suggestion_text=" | ".join(suggestions_text),
            confidence_score=0.8,
            factors_json={
                "required_hours": required_hours,
                "total_available": total_available,
                "shortage": shortage,
                "available_users_count": len(available_users)
            },
            created_at=datetime.utcnow()
        )
        self.db.add(suggestion_record)
        self.db.commit()
        
        return {
            "id": str(suggestion_record.id),
            "type": "capacity_crunch",
            "severity": "HIGH" if shortage > required_hours * 0.5 else "MODERATE",
            "shortage_hours": round(shortage, 1),
            "suggestions": suggestions_text,
            "recommended_actions": actions,
            "available_users": [
                {
                    "user_id": u["user_id"],
                    "user_name": u["user_name"],
                    "remaining_hours": u["remaining_hours"]
                }
                for u in available_users
            ]
        }
    
    def _get_historical_performance(self, role: Role) -> Dict[str, Dict]:
        """Get historical performance data for learning"""
        # Query historical data
        history = self.db.query(CapacityHistory).filter(
            CapacityHistory.role == role
        ).all()
        
        performance = {}
        for h in history:
            user_id = str(h.user_id)
            if user_id not in performance:
                performance[user_id] = {
                    "total_planned": 0,
                    "total_actual": 0,
                    "entries": 0
                }
            performance[user_id]["total_planned"] += h.planned_hours
            performance[user_id]["total_actual"] += h.actual_hours
            performance[user_id]["entries"] += 1
        
        # Calculate efficiency scores
        for user_id, data in performance.items():
            if data["total_planned"] > 0:
                data["efficiency_score"] = data["total_actual"] / data["total_planned"]
            else:
                data["efficiency_score"] = 1.0
        
        return performance
    
    def record_suggestion_feedback(
        self,
        suggestion_id: UUID,
        was_accepted: bool,
        feedback_notes: Optional[str] = None,
        actual_outcome: Optional[str] = None
    ) -> CapacitySuggestion:
        """Record feedback on a suggestion for learning"""
        suggestion = self.db.query(CapacitySuggestion).filter(
            CapacitySuggestion.id == suggestion_id
        ).first()
        
        if not suggestion:
            raise ValueError("Suggestion not found")
        
        suggestion.was_accepted = was_accepted
        suggestion.feedback_notes = feedback_notes
        suggestion.actual_outcome = actual_outcome
        suggestion.feedback_at = datetime.utcnow()
        
        self.db.commit()
        return suggestion
    
    def record_manual_input(
        self,
        input_type: str,
        created_by_user_id: UUID,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        role: Optional[Role] = None,
        region: Optional[Region] = None,
        value_numeric: Optional[float] = None,
        value_text: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> CapacityManualInput:
        """Record manual capacity input for learning"""
        manual_input = CapacityManualInput(
            input_type=input_type,
            user_id=user_id,
            project_id=project_id,
            role=role,
            region=region,
            value_numeric=value_numeric,
            value_text=value_text,
            context_json=context or {},
            created_by_user_id=created_by_user_id,
            created_at=datetime.utcnow()
        )
        self.db.add(manual_input)
        self.db.commit()
        return manual_input


def get_capacity_service(db: Session) -> CapacityService:
    """Factory function for CapacityService"""
    return CapacityService(db)


def get_suggestion_service(db: Session) -> CapacitySuggestionService:
    """Factory function for CapacitySuggestionService"""
    return CapacitySuggestionService(db)
