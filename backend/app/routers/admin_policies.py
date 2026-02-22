"""Admin policies: GET/PUT PolicyConfig (Admin/Manager only)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_active_user
from app.models import User, PolicyConfig
from app.rbac import require_admin_manager
from app.schemas import PolicyConfigResponse, PolicyConfigValue
from app.config import settings

router = APIRouter(prefix="/admin/policies", tags=["admin-policies"])

DEFAULT_POLICY_KEY = "default"


def _default_value_json() -> dict:
    return {
        "reminder_cadence_hours": settings.POLICY_REMINDER_CADENCE_HOURS,
        "max_reminders": settings.POLICY_MAX_REMINDERS,
        "idle_minutes": settings.POLICY_IDLE_MINUTES,
        "build_retry_cap": settings.POLICY_BUILD_RETRY_CAP,
        "defect_validation_cycle_cap": settings.POLICY_DEFECT_VALIDATION_CYCLE_CAP,
        "pass_threshold_percent": settings.POLICY_PASS_THRESHOLD_PERCENT,
        "lighthouse_thresholds_json": {"performance": 95, "accessibility": 98, "best_practices": 95, "seo": 95},
        "axe_policy_json": {"block": ["serious", "critical"], "allow_medium_minor_if_total_under": 5},
        "proof_pack_soft_mb": settings.POLICY_PROOF_PACK_SOFT_MB,
        "proof_pack_hard_mb": settings.POLICY_PROOF_PACK_HARD_MB,
    }


@router.get("", response_model=PolicyConfigResponse)
def get_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get policy config (Admin/Manager). Returns default row or creates from env defaults."""
    require_admin_manager(current_user)
    row = db.query(PolicyConfig).filter(PolicyConfig.key == DEFAULT_POLICY_KEY).first()
    if not row:
        row = PolicyConfig(key=DEFAULT_POLICY_KEY, value_json=_default_value_json())
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.put("", response_model=PolicyConfigResponse)
def put_policies(
    body: PolicyConfigValue,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update policy config (Admin/Manager). Merges with existing; all fields optional."""
    require_admin_manager(current_user)
    row = db.query(PolicyConfig).filter(PolicyConfig.key == DEFAULT_POLICY_KEY).first()
    data = body.model_dump(exclude_unset=True)
    if not row:
        value = _default_value_json()
        value.update(data)
        row = PolicyConfig(key=DEFAULT_POLICY_KEY, value_json=value)
        db.add(row)
    else:
        value = dict(row.value_json) if isinstance(row.value_json, dict) else {}
        value.update(data)
        row.value_json = value
    db.commit()
    db.refresh(row)
    return row
