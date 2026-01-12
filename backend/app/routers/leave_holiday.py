"""
Leave and Holiday Management Router
Handles user leaves, region-specific holidays, and company holidays
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel

from app.db import get_db
from app.deps import get_current_user
from app.models import (
    User, Role, Region, UserLeave, LeaveType, LeaveStatus,
    RegionHoliday, CompanyHoliday, LeaveEntitlementType,
    LeaveEntitlementPolicy, UserLeaveBalance, CalendarProvider,
    CalendarConnection, MeetingBlock, TimeEntry, CapacityAdjustment
)
from app.rbac import check_admin_or_manager
from app.services.capacity_service import CapacityService

router = APIRouter(prefix="/leave-holiday", tags=["Leave & Holiday"])


# ==================== Schemas ====================

class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None
    partial_day: bool = False
    hours_off: Optional[float] = None


class LeaveRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    leave_type: str
    start_date: date
    end_date: date
    status: str
    reason: Optional[str]
    partial_day: bool
    hours_off: Optional[float]
    approved_by_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class RegionHolidayCreate(BaseModel):
    region: Region
    name: str
    date: date
    year: int
    is_optional: bool = False
    description: Optional[str] = None


class RegionHolidayResponse(BaseModel):
    id: UUID
    region: str
    name: str
    date: date
    year: int
    is_optional: bool
    description: Optional[str]

    class Config:
        from_attributes = True


class CompanyHolidayCreate(BaseModel):
    name: str
    date: date
    year: int
    description: Optional[str] = None


class CompanyHolidayResponse(BaseModel):
    id: UUID
    name: str
    date: date
    year: int
    description: Optional[str]

    class Config:
        from_attributes = True


class AvailabilityResponse(BaseModel):
    user_id: UUID
    user_name: str
    start_date: date
    end_date: date
    leaves: List[dict]
    holidays: List[dict]
    total_unavailable_days: int
    working_days: int
    available_days: int


# ==================== Leave Endpoints ====================

@router.post("/leaves", response_model=LeaveRequestResponse)
def create_leave_request(
    leave_data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new leave request"""
    if leave_data.end_date < leave_data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )
    
    # Check for overlapping leaves
    existing_leave = db.query(UserLeave).filter(
        UserLeave.user_id == current_user.id,
        UserLeave.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
        UserLeave.start_date <= leave_data.end_date,
        UserLeave.end_date >= leave_data.start_date
    ).first()
    
    if existing_leave:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a leave request for this period"
        )
    
    leave = UserLeave(
        user_id=current_user.id,
        leave_type=leave_data.leave_type,
        start_date=leave_data.start_date,
        end_date=leave_data.end_date,
        reason=leave_data.reason,
        partial_day=leave_data.partial_day,
        hours_off=leave_data.hours_off,
        status=LeaveStatus.PENDING,
        created_at=datetime.utcnow()
    )
    
    db.add(leave)
    db.commit()
    db.refresh(leave)
    
    return LeaveRequestResponse(
        id=leave.id,
        user_id=leave.user_id,
        user_name=current_user.name,
        leave_type=leave.leave_type.value,
        start_date=leave.start_date,
        end_date=leave.end_date,
        status=leave.status.value,
        reason=leave.reason,
        partial_day=leave.partial_day,
        hours_off=leave.hours_off,
        approved_by_name=None,
        created_at=leave.created_at
    )


@router.get("/leaves/my", response_model=List[LeaveRequestResponse])
def get_my_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's leave requests"""
    leaves = db.query(UserLeave).filter(
        UserLeave.user_id == current_user.id
    ).order_by(UserLeave.start_date.desc()).all()
    
    return [
        LeaveRequestResponse(
            id=leave.id,
            user_id=leave.user_id,
            user_name=current_user.name,
            leave_type=leave.leave_type.value,
            start_date=leave.start_date,
            end_date=leave.end_date,
            status=leave.status.value,
            reason=leave.reason,
            partial_day=leave.partial_day,
            hours_off=leave.hours_off,
            approved_by_name=leave.approved_by.name if leave.approved_by else None,
            created_at=leave.created_at
        )
        for leave in leaves
    ]


@router.get("/leaves/pending", response_model=List[LeaveRequestResponse])
def get_pending_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending leave requests (admin/manager only)"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    leaves = db.query(UserLeave).filter(
        UserLeave.status == LeaveStatus.PENDING
    ).order_by(UserLeave.created_at.desc()).all()
    
    return [
        LeaveRequestResponse(
            id=leave.id,
            user_id=leave.user_id,
            user_name=leave.user.name,
            leave_type=leave.leave_type.value,
            start_date=leave.start_date,
            end_date=leave.end_date,
            status=leave.status.value,
            reason=leave.reason,
            partial_day=leave.partial_day,
            hours_off=leave.hours_off,
            approved_by_name=None,
            created_at=leave.created_at
        )
        for leave in leaves
    ]


@router.get("/leaves/team", response_model=List[LeaveRequestResponse])
def get_team_leaves(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get approved leaves for team members in date range"""
    leaves = db.query(UserLeave).filter(
        UserLeave.status == LeaveStatus.APPROVED,
        UserLeave.start_date <= end_date,
        UserLeave.end_date >= start_date
    ).order_by(UserLeave.start_date).all()
    
    return [
        LeaveRequestResponse(
            id=leave.id,
            user_id=leave.user_id,
            user_name=leave.user.name,
            leave_type=leave.leave_type.value,
            start_date=leave.start_date,
            end_date=leave.end_date,
            status=leave.status.value,
            reason=leave.reason,
            partial_day=leave.partial_day,
            hours_off=leave.hours_off,
            approved_by_name=leave.approved_by.name if leave.approved_by else None,
            created_at=leave.created_at
        )
        for leave in leaves
    ]


@router.put("/leaves/{leave_id}/approve")
def approve_leave(
    leave_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a leave request"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    leave = db.query(UserLeave).filter(UserLeave.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave.status != LeaveStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Leave is already {leave.status.value}"
        )
    
    leave.status = LeaveStatus.APPROVED
    leave.approved_by_user_id = current_user.id
    leave.approved_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Leave approved", "leave_id": str(leave_id)}


@router.put("/leaves/{leave_id}/reject")
def reject_leave(
    leave_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a leave request"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    leave = db.query(UserLeave).filter(UserLeave.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave.status != LeaveStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Leave is already {leave.status.value}"
        )
    
    leave.status = LeaveStatus.REJECTED
    leave.approved_by_user_id = current_user.id
    leave.approved_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Leave rejected", "leave_id": str(leave_id)}


@router.delete("/leaves/{leave_id}")
def cancel_leave(
    leave_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a leave request"""
    leave = db.query(UserLeave).filter(UserLeave.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    # Only owner or admin/manager can cancel
    if leave.user_id != current_user.id and current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this leave")
    
    if leave.status == LeaveStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave is already cancelled"
        )
    
    leave.status = LeaveStatus.CANCELLED
    leave.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Leave cancelled", "leave_id": str(leave_id)}


# ==================== Holiday Endpoints ====================

@router.get("/holidays/region/{region}", response_model=List[RegionHolidayResponse])
def get_region_holidays(
    region: Region,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get holidays for a specific region"""
    query = db.query(RegionHoliday).filter(RegionHoliday.region == region)
    if year:
        query = query.filter(RegionHoliday.year == year)
    holidays = query.order_by(RegionHoliday.date).all()
    
    return [
        RegionHolidayResponse(
            id=h.id,
            region=h.region.value,
            name=h.name,
            date=h.date,
            year=h.year,
            is_optional=h.is_optional,
            description=h.description
        )
        for h in holidays
    ]


@router.post("/holidays/region", response_model=RegionHolidayResponse)
def create_region_holiday(
    holiday_data: RegionHolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new region-specific holiday"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    # Check for duplicate
    existing = db.query(RegionHoliday).filter(
        RegionHoliday.region == holiday_data.region,
        RegionHoliday.date == holiday_data.date
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Holiday already exists for this region on this date"
        )
    
    holiday = RegionHoliday(
        region=holiday_data.region,
        name=holiday_data.name,
        date=holiday_data.date,
        year=holiday_data.year,
        is_optional=holiday_data.is_optional,
        description=holiday_data.description,
        created_at=datetime.utcnow()
    )
    
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    
    return RegionHolidayResponse(
        id=holiday.id,
        region=holiday.region.value,
        name=holiday.name,
        date=holiday.date,
        year=holiday.year,
        is_optional=holiday.is_optional,
        description=holiday.description
    )


@router.delete("/holidays/region/{holiday_id}")
def delete_region_holiday(
    holiday_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a region holiday"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    holiday = db.query(RegionHoliday).filter(RegionHoliday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    
    db.delete(holiday)
    db.commit()
    
    return {"message": "Holiday deleted", "holiday_id": str(holiday_id)}


@router.get("/holidays/company", response_model=List[CompanyHolidayResponse])
def get_company_holidays(
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get company-wide holidays"""
    query = db.query(CompanyHoliday)
    if year:
        query = query.filter(CompanyHoliday.year == year)
    holidays = query.order_by(CompanyHoliday.date).all()
    
    return [
        CompanyHolidayResponse(
            id=h.id,
            name=h.name,
            date=h.date,
            year=h.year,
            description=h.description
        )
        for h in holidays
    ]


@router.post("/holidays/company", response_model=CompanyHolidayResponse)
def create_company_holiday(
    holiday_data: CompanyHolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new company-wide holiday"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    # Check for duplicate
    existing = db.query(CompanyHoliday).filter(
        CompanyHoliday.date == holiday_data.date
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company holiday already exists on this date"
        )
    
    holiday = CompanyHoliday(
        name=holiday_data.name,
        date=holiday_data.date,
        year=holiday_data.year,
        description=holiday_data.description,
        created_at=datetime.utcnow()
    )
    
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    
    return CompanyHolidayResponse(
        id=holiday.id,
        name=holiday.name,
        date=holiday.date,
        year=holiday.year,
        description=holiday.description
    )


@router.delete("/holidays/company/{holiday_id}")
def delete_company_holiday(
    holiday_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a company holiday"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    holiday = db.query(CompanyHoliday).filter(CompanyHoliday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    
    db.delete(holiday)
    db.commit()
    
    return {"message": "Holiday deleted", "holiday_id": str(holiday_id)}


# ==================== Availability Endpoints ====================

@router.get("/availability/{user_id}", response_model=AvailabilityResponse)
def get_user_availability(
    user_id: UUID,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user availability accounting for leaves and holidays"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    capacity_service = CapacityService(db)
    unavailable_info = capacity_service.get_user_unavailable_dates(user_id, start_date, end_date)
    
    # Calculate working days (weekdays)
    from datetime import timedelta
    working_days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Monday to Friday
            working_days += 1
        current += timedelta(days=1)
    
    available_days = working_days - unavailable_info["total_unavailable_days"]
    
    return AvailabilityResponse(
        user_id=user_id,
        user_name=user.name,
        start_date=start_date,
        end_date=end_date,
        leaves=unavailable_info["leaves"],
        holidays=unavailable_info["holidays"],
        total_unavailable_days=unavailable_info["total_unavailable_days"],
        working_days=working_days,
        available_days=available_days
    )


@router.get("/availability/team-calendar")
def get_team_calendar(
    start_date: date,
    end_date: date,
    region: Optional[Region] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get team availability calendar view"""
    # Get all active users (optionally filtered by region)
    query = db.query(User).filter(
        User.is_active == True,
        User.is_archived == False
    )
    if region:
        query = query.filter(User.region == region)
    users = query.all()
    
    capacity_service = CapacityService(db)
    
    calendar_data = []
    for user in users:
        unavailable = capacity_service.get_user_unavailable_dates(user.id, start_date, end_date)
        calendar_data.append({
            "user_id": str(user.id),
            "user_name": user.name,
            "role": user.role.value,
            "region": user.region.value if user.region else None,
            "leaves": unavailable["leaves"],
            "holidays": unavailable["holidays"],
            "unavailable_days": unavailable["total_unavailable_days"]
        })
    
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "team_members": calendar_data
    }


# ==================== Leave Entitlement Policy Endpoints ====================

class LeaveEntitlementPolicyCreate(BaseModel):
    leave_type: LeaveEntitlementType
    role: Optional[Role] = None
    region: Optional[Region] = None
    annual_days: float
    can_carry_forward: bool = False
    max_carry_forward_days: float = 0
    requires_approval: bool = True
    min_notice_days: int = 0
    max_consecutive_days: Optional[int] = None


class LeaveEntitlementPolicyResponse(BaseModel):
    id: UUID
    leave_type: str
    role: Optional[str]
    region: Optional[str]
    annual_days: float
    can_carry_forward: bool
    max_carry_forward_days: float
    requires_approval: bool
    min_notice_days: int
    max_consecutive_days: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/entitlement-policies", response_model=List[LeaveEntitlementPolicyResponse])
def get_entitlement_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all leave entitlement policies"""
    policies = db.query(LeaveEntitlementPolicy).filter(
        LeaveEntitlementPolicy.is_active == True
    ).all()
    
    return [
        LeaveEntitlementPolicyResponse(
            id=p.id,
            leave_type=p.leave_type.value,
            role=p.role.value if p.role else None,
            region=p.region.value if p.region else None,
            annual_days=p.annual_days,
            can_carry_forward=p.can_carry_forward,
            max_carry_forward_days=p.max_carry_forward_days,
            requires_approval=p.requires_approval,
            min_notice_days=p.min_notice_days,
            max_consecutive_days=p.max_consecutive_days,
            is_active=p.is_active
        )
        for p in policies
    ]


@router.post("/entitlement-policies", response_model=LeaveEntitlementPolicyResponse)
def create_entitlement_policy(
    policy_data: LeaveEntitlementPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new leave entitlement policy"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    # Check for existing policy
    existing = db.query(LeaveEntitlementPolicy).filter(
        LeaveEntitlementPolicy.leave_type == policy_data.leave_type,
        LeaveEntitlementPolicy.role == policy_data.role,
        LeaveEntitlementPolicy.region == policy_data.region,
        LeaveEntitlementPolicy.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Policy already exists for this leave type/role/region combination"
        )
    
    policy = LeaveEntitlementPolicy(
        leave_type=policy_data.leave_type,
        role=policy_data.role,
        region=policy_data.region,
        annual_days=policy_data.annual_days,
        can_carry_forward=policy_data.can_carry_forward,
        max_carry_forward_days=policy_data.max_carry_forward_days,
        requires_approval=policy_data.requires_approval,
        min_notice_days=policy_data.min_notice_days,
        max_consecutive_days=policy_data.max_consecutive_days,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    return LeaveEntitlementPolicyResponse(
        id=policy.id,
        leave_type=policy.leave_type.value,
        role=policy.role.value if policy.role else None,
        region=policy.region.value if policy.region else None,
        annual_days=policy.annual_days,
        can_carry_forward=policy.can_carry_forward,
        max_carry_forward_days=policy.max_carry_forward_days,
        requires_approval=policy.requires_approval,
        min_notice_days=policy.min_notice_days,
        max_consecutive_days=policy.max_consecutive_days,
        is_active=policy.is_active
    )


@router.put("/entitlement-policies/{policy_id}", response_model=LeaveEntitlementPolicyResponse)
def update_entitlement_policy(
    policy_id: UUID,
    policy_data: LeaveEntitlementPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a leave entitlement policy"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    policy = db.query(LeaveEntitlementPolicy).filter(LeaveEntitlementPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    policy.annual_days = policy_data.annual_days
    policy.can_carry_forward = policy_data.can_carry_forward
    policy.max_carry_forward_days = policy_data.max_carry_forward_days
    policy.requires_approval = policy_data.requires_approval
    policy.min_notice_days = policy_data.min_notice_days
    policy.max_consecutive_days = policy_data.max_consecutive_days
    policy.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(policy)
    
    return LeaveEntitlementPolicyResponse(
        id=policy.id,
        leave_type=policy.leave_type.value,
        role=policy.role.value if policy.role else None,
        region=policy.region.value if policy.region else None,
        annual_days=policy.annual_days,
        can_carry_forward=policy.can_carry_forward,
        max_carry_forward_days=policy.max_carry_forward_days,
        requires_approval=policy.requires_approval,
        min_notice_days=policy.min_notice_days,
        max_consecutive_days=policy.max_consecutive_days,
        is_active=policy.is_active
    )


# ==================== User Leave Balance Endpoints ====================

class LeaveBalanceResponse(BaseModel):
    id: UUID
    user_id: UUID
    leave_type: str
    year: int
    entitled_days: float
    used_days: float
    pending_days: float
    carried_forward: float
    adjusted_days: float
    available_days: float

    class Config:
        from_attributes = True


class LeaveBalanceAdjust(BaseModel):
    adjustment_days: float
    reason: str


@router.get("/balances/my", response_model=List[LeaveBalanceResponse])
def get_my_leave_balances(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's leave balances"""
    if year is None:
        year = date.today().year
    
    # Get or create balances based on policies
    balances = _get_or_create_user_balances(db, current_user, year)
    
    return [
        LeaveBalanceResponse(
            id=b.id,
            user_id=b.user_id,
            leave_type=b.leave_type.value,
            year=b.year,
            entitled_days=b.entitled_days,
            used_days=b.used_days,
            pending_days=b.pending_days,
            carried_forward=b.carried_forward,
            adjusted_days=b.adjusted_days,
            available_days=b.available_days
        )
        for b in balances
    ]


@router.get("/balances/user/{user_id}", response_model=List[LeaveBalanceResponse])
def get_user_leave_balances(
    user_id: UUID,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific user's leave balances (admin/manager only)"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if year is None:
        year = date.today().year
    
    balances = _get_or_create_user_balances(db, user, year)
    
    return [
        LeaveBalanceResponse(
            id=b.id,
            user_id=b.user_id,
            leave_type=b.leave_type.value,
            year=b.year,
            entitled_days=b.entitled_days,
            used_days=b.used_days,
            pending_days=b.pending_days,
            carried_forward=b.carried_forward,
            adjusted_days=b.adjusted_days,
            available_days=b.available_days
        )
        for b in balances
    ]


@router.put("/balances/{balance_id}/adjust")
def adjust_leave_balance(
    balance_id: UUID,
    adjustment: LeaveBalanceAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually adjust a user's leave balance"""
    # Check admin/manager role
    check_admin_or_manager(current_user)
    balance = db.query(UserLeaveBalance).filter(UserLeaveBalance.id == balance_id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")
    
    balance.adjusted_days += adjustment.adjustment_days
    balance.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Balance adjusted",
        "new_adjusted_days": balance.adjusted_days,
        "new_available_days": balance.available_days
    }


def _get_or_create_user_balances(db: Session, user: User, year: int) -> List[UserLeaveBalance]:
    """Get or create user leave balances based on applicable policies and date of joining"""
    # Get existing balances
    existing = db.query(UserLeaveBalance).filter(
        UserLeaveBalance.user_id == user.id,
        UserLeaveBalance.year == year
    ).all()
    
    existing_types = {b.leave_type for b in existing}
    
    # Get applicable policies
    policies = db.query(LeaveEntitlementPolicy).filter(
        LeaveEntitlementPolicy.is_active == True
    ).all()
    
    # Filter to most specific policies for each leave type
    applicable_policies = {}
    for policy in policies:
        # Check if policy applies to this user
        role_match = policy.role is None or policy.role == user.role
        region_match = policy.region is None or policy.region == user.region
        
        if role_match and region_match:
            leave_type = policy.leave_type
            # Prefer more specific policies (with role/region specified)
            specificity = (1 if policy.role else 0) + (1 if policy.region else 0)
            
            if leave_type not in applicable_policies:
                applicable_policies[leave_type] = (policy, specificity)
            elif specificity > applicable_policies[leave_type][1]:
                applicable_policies[leave_type] = (policy, specificity)
    
    # Calculate prorated entitlement based on date of joining
    def calculate_entitled_days(policy, user, year):
        """Calculate entitled days based on policy type and date of joining"""
        annual_days = policy.annual_days
        
        # If no date of joining, assume full year
        if not user.date_of_joining:
            return annual_days
        
        doj = user.date_of_joining
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        today = date.today()
        
        # If joined after this year, no entitlement
        if doj.year > year:
            return 0
        
        # Special handling for EARNED leave (1.25 per month)
        if policy.leave_type == LeaveEntitlementType.EARNED:
            if doj.year < year:
                # Full year if joined before this year
                months_worked = 12
            else:
                # Months from joining to end of year (or today if current year)
                end_month = today.month if year == today.year else 12
                months_worked = end_month - doj.month + 1
                if months_worked < 0:
                    months_worked = 0
            
            # 1.25 days per month
            earned = months_worked * 1.25
            return round(earned, 2)
        
        # For other leave types, prorate if joined mid-year
        if doj.year == year:
            # Calculate fraction of year from joining date
            days_in_year = (year_end - year_start).days + 1
            days_worked = (year_end - doj).days + 1
            proration_factor = days_worked / days_in_year
            return round(annual_days * proration_factor, 2)
        
        # Joined before this year - full entitlement
        return annual_days
    
    # Create missing balances
    for leave_type, (policy, _) in applicable_policies.items():
        if leave_type not in existing_types:
            # Calculate entitled days based on DOJ
            entitled_days = calculate_entitled_days(policy, user, year)
            
            # Check for carry forward from previous year
            carried = 0
            if policy.can_carry_forward:
                prev_balance = db.query(UserLeaveBalance).filter(
                    UserLeaveBalance.user_id == user.id,
                    UserLeaveBalance.leave_type == leave_type,
                    UserLeaveBalance.year == year - 1
                ).first()
                if prev_balance:
                    available = prev_balance.available_days
                    carried = min(available, policy.max_carry_forward_days)
            
            balance = UserLeaveBalance(
                user_id=user.id,
                leave_type=leave_type,
                year=year,
                entitled_days=entitled_days,
                carried_forward=carried,
                created_at=datetime.utcnow()
            )
            db.add(balance)
            existing.append(balance)
    
    db.commit()
    return existing


# ==================== Calendar Sync Endpoints ====================

class MeetingBlockCreate(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    is_busy: bool = True
    category: Optional[str] = None


class MeetingBlockResponse(BaseModel):
    id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    is_busy: bool
    category: Optional[str]
    duration_hours: float

    class Config:
        from_attributes = True


@router.get("/meetings/my")
def get_my_meetings(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's meetings for date range"""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    meetings = db.query(MeetingBlock).filter(
        MeetingBlock.user_id == current_user.id,
        MeetingBlock.start_time >= start_dt,
        MeetingBlock.end_time <= end_dt
    ).order_by(MeetingBlock.start_time).all()
    
    # Calculate total meeting hours
    total_hours = sum(m.duration_hours for m in meetings if m.is_busy)
    
    return {
        "meetings": [
            {
                "id": str(m.id),
                "title": m.title,
                "start_time": m.start_time.isoformat(),
                "end_time": m.end_time.isoformat(),
                "is_all_day": m.is_all_day,
                "is_busy": m.is_busy,
                "category": m.category,
                "duration_hours": round(m.duration_hours, 2)
            }
            for m in meetings
        ],
        "total_meeting_hours": round(total_hours, 2),
        "meeting_count": len(meetings)
    }


@router.post("/meetings")
def create_meeting(
    meeting_data: MeetingBlockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually add a meeting block"""
    meeting = MeetingBlock(
        user_id=current_user.id,
        title=meeting_data.title,
        start_time=meeting_data.start_time,
        end_time=meeting_data.end_time,
        is_all_day=meeting_data.is_all_day,
        is_busy=meeting_data.is_busy,
        category=meeting_data.category,
        created_at=datetime.utcnow()
    )
    
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    return {
        "id": str(meeting.id),
        "message": "Meeting added",
        "duration_hours": meeting.duration_hours
    }


@router.delete("/meetings/{meeting_id}")
def delete_meeting(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a meeting block"""
    meeting = db.query(MeetingBlock).filter(
        MeetingBlock.id == meeting_id,
        MeetingBlock.user_id == current_user.id
    ).first()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    db.delete(meeting)
    db.commit()
    
    return {"message": "Meeting deleted"}


# ==================== Comprehensive Capacity Endpoints ====================

@router.get("/capacity/detailed/{user_id}")
def get_detailed_capacity(
    user_id: UUID,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive capacity breakdown for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    from datetime import timedelta
    
    # Get config for daily hours
    capacity_service = CapacityService(db)
    config = capacity_service.get_capacity_config(user.role, user.region)
    daily_hours = config.daily_hours
    buffer_pct = config.buffer_percentage / 100
    
    # Calculate working days
    working_days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            working_days += 1
        current += timedelta(days=1)
    
    # Base capacity
    base_capacity = working_days * daily_hours
    
    # Get unavailable days (leaves + holidays)
    unavailable = capacity_service.get_user_unavailable_dates(user_id, start_date, end_date)
    leave_days = unavailable["total_unavailable_days"]
    leave_hours = leave_days * daily_hours
    
    # Get meeting hours
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    meetings = db.query(MeetingBlock).filter(
        MeetingBlock.user_id == user_id,
        MeetingBlock.is_busy == True,
        MeetingBlock.start_time >= start_dt,
        MeetingBlock.end_time <= end_dt
    ).all()
    meeting_hours = sum(m.duration_hours for m in meetings)
    
    # Get capacity adjustments
    adjustments = db.query(CapacityAdjustment).filter(
        CapacityAdjustment.user_id == user_id,
        CapacityAdjustment.is_active == True,
        CapacityAdjustment.start_date <= end_date,
        CapacityAdjustment.end_date >= start_date
    ).all()
    adjustment_hours = sum(a.daily_hours_adjustment * min(
        (min(a.end_date, end_date) - max(a.start_date, start_date)).days + 1,
        working_days
    ) for a in adjustments)
    
    # Calculate buffer
    buffer_hours = base_capacity * buffer_pct
    
    # Net available capacity
    net_capacity = base_capacity - leave_hours - meeting_hours - buffer_hours + adjustment_hours
    
    # Get current allocations
    allocations = db.query(CapacityAllocation).filter(
        CapacityAllocation.user_id == user_id,
        CapacityAllocation.date >= start_date,
        CapacityAllocation.date <= end_date
    ).all() if hasattr(db.query(CapacityAllocation), 'filter') else []
    
    try:
        from app.models import CapacityAllocation
        allocations = db.query(CapacityAllocation).filter(
            CapacityAllocation.user_id == user_id,
            CapacityAllocation.date >= start_date,
            CapacityAllocation.date <= end_date
        ).all()
        allocated_hours = sum(a.allocated_hours for a in allocations)
    except:
        allocated_hours = 0
    
    remaining_capacity = max(0, net_capacity - allocated_hours)
    
    return {
        "user_id": str(user_id),
        "user_name": user.name,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "working_days": working_days
        },
        "capacity_breakdown": {
            "base_capacity_hours": round(base_capacity, 1),
            "daily_hours": daily_hours,
            "deductions": {
                "leave_hours": round(leave_hours, 1),
                "leave_days": leave_days,
                "meeting_hours": round(meeting_hours, 1),
                "buffer_hours": round(buffer_hours, 1),
                "buffer_percentage": buffer_pct * 100
            },
            "adjustments": {
                "hours": round(adjustment_hours, 1),
                "details": [
                    {
                        "type": a.adjustment_type,
                        "hours": a.daily_hours_adjustment,
                        "reason": a.reason
                    }
                    for a in adjustments
                ]
            },
            "net_available_hours": round(net_capacity, 1),
            "allocated_hours": round(allocated_hours, 1),
            "remaining_hours": round(remaining_capacity, 1)
        },
        "utilization": {
            "percentage": round((allocated_hours / net_capacity * 100) if net_capacity > 0 else 0, 1),
            "status": _get_utilization_status(allocated_hours / net_capacity * 100 if net_capacity > 0 else 0)
        },
        "upcoming_blockers": {
            "leaves": unavailable["leaves"],
            "holidays": unavailable["holidays"],
            "meeting_count": len(meetings)
        }
    }


def _get_utilization_status(pct: float) -> str:
    if pct < 50:
        return "LOW"
    elif pct < 70:
        return "MODERATE"
    elif pct < 85:
        return "HIGH"
    else:
        return "CRITICAL"


# ==================== Team Capacity Overview ====================

@router.get("/capacity/team-overview")
def get_team_capacity_overview(
    start_date: date,
    end_date: date,
    role: Optional[Role] = None,
    region: Optional[Region] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get team capacity overview with all factors"""
    # Get active delivery roles only
    delivery_roles = [Role.CONSULTANT, Role.PC, Role.BUILDER, Role.TESTER]
    
    query = db.query(User).filter(
        User.is_active == True,
        User.is_archived == False,
        User.role.in_(delivery_roles)
    )
    
    if role:
        query = query.filter(User.role == role)
    if region:
        query = query.filter(User.region == region)
    
    users = query.all()
    
    team_data = []
    total_available = 0
    total_allocated = 0
    
    for user in users:
        try:
            # Get detailed capacity (simplified call)
            from datetime import timedelta
            capacity_service = CapacityService(db)
            config = capacity_service.get_capacity_config(user.role, user.region)
            
            working_days = sum(1 for i in range((end_date - start_date).days + 1) 
                             if (start_date + timedelta(days=i)).weekday() < 5)
            base_hours = working_days * config.daily_hours
            
            unavailable = capacity_service.get_user_unavailable_dates(user.id, start_date, end_date)
            leave_hours = unavailable["total_unavailable_days"] * config.daily_hours
            
            net_hours = base_hours - leave_hours - (base_hours * config.buffer_percentage / 100)
            
            team_data.append({
                "user_id": str(user.id),
                "user_name": user.name,
                "role": user.role.value,
                "region": user.region.value if user.region else None,
                "available_hours": round(net_hours, 1),
                "leave_days": unavailable["total_unavailable_days"],
                "has_upcoming_leave": len(unavailable["leaves"]) > 0
            })
            total_available += net_hours
        except Exception as e:
            print(f"Error calculating capacity for {user.name}: {e}")
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "summary": {
            "total_team_members": len(team_data),
            "total_available_hours": round(total_available, 1),
            "members_on_leave": sum(1 for t in team_data if t["has_upcoming_leave"])
        },
        "by_role": _group_by_role(team_data),
        "by_region": _group_by_region(team_data),
        "team_members": team_data
    }


def _group_by_role(team_data: list) -> dict:
    result = {}
    for member in team_data:
        role = member["role"]
        if role not in result:
            result[role] = {"count": 0, "total_hours": 0}
        result[role]["count"] += 1
        result[role]["total_hours"] += member["available_hours"]
    return result


def _group_by_region(team_data: list) -> dict:
    result = {}
    for member in team_data:
        region = member["region"] or "Unknown"
        if region not in result:
            result[region] = {"count": 0, "total_hours": 0}
        result[region]["count"] += 1
        result[region]["total_hours"] += member["available_hours"]
    return result
