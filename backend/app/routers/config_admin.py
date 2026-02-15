from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.schemas import AdminConfigResponse, AdminConfigUpdate, PreviewStrategy
from app.deps import get_current_active_user
from app.services import config_service
from app.rbac import require_admin_manager
from typing import List, Optional

router = APIRouter(prefix="/admin/config", tags=["admin-config"])


@router.get("", response_model=List[AdminConfigResponse])
def list_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all configuration keys (Admin/Manager only)"""
    require_admin_manager(current_user)
    
    configs = config_service.get_all_configs(db)
    return configs


# ---------- Specific paths must be declared before /{key} ----------
# ---------- Template metrics aggregator (Prompt 9) ----------
@router.post("/run-template-metrics")
def run_template_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Run aggregate_template_performance job (Admin/Manager)."""
    require_admin_manager(current_user)
    from app.jobs.template_metrics_aggregator import aggregate_template_performance
    result = aggregate_template_performance(db=db)
    return result


# ---------- Learning proposals (Prompt 9, shadow mode) ----------
@router.get("/learning-proposals")
def get_learning_proposals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current learning proposals from config (Admin/Manager)."""
    require_admin_manager(current_user)
    from app.policies.learning_engine import get_learning_proposals
    proposals = get_learning_proposals(db)
    return {"proposals": proposals}


@router.post("/learning-proposals/run")
def run_learning_proposals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Compute and save learning proposals (Admin/Manager). Does not apply."""
    require_admin_manager(current_user)
    from app.policies.learning_engine import run_learning_and_save
    proposals = run_learning_and_save(db)
    return {"proposals": proposals, "message": "Proposals computed and saved"}


@router.post("/learning-proposals/apply")
def apply_learning_proposal(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Apply one learning proposal by index (Admin/Manager). Updates actual config."""
    require_admin_manager(current_user)
    index = body.get("index")
    if index is None:
        raise HTTPException(status_code=400, detail="index required")
    from app.policies.learning_engine import get_learning_proposals, save_learning_proposals
    from app.models import AdminConfig
    proposals = get_learning_proposals(db)
    if index < 0 or index >= len(proposals):
        raise HTTPException(status_code=404, detail="Proposal not found")
    prop = proposals[index]
    key = prop.get("policy_key")
    suggested = prop.get("suggested_value")
    if not key:
        raise HTTPException(status_code=400, detail="Invalid proposal")
    # Apply: update the config key (e.g. global_thresholds_json)
    if key == "assignment_engine.WEIGHT_PERFORMANCE":
        # Assignment weights are in code; we could store override in AdminConfig
        config_service.update_config(db, "assignment_weight_overrides", {"WEIGHT_PERFORMANCE": suggested}, current_user)
    elif key.startswith("global_thresholds_json."):
        import copy
        config = config_service.get_config(db, "global_thresholds_json")
        val = copy.deepcopy(config.value_json) if config and isinstance(config.value_json, dict) else {}
        parts = key.split(".")[1:]
        cur = val
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = suggested
        config_service.update_config(db, "global_thresholds_json", val, current_user)
    else:
        # Generic: store in learning_applied_json or similar
        config_service.update_config(db, "learning_applied_json", {key: suggested}, current_user)
    # Remove applied proposal from list
    proposals.pop(index)
    save_learning_proposals(db, proposals)
    return {"message": "Proposal applied", "remaining": len(proposals)}


# ---------- Generic config by key (must be after specific paths) ----------
@router.get("/{key}", response_model=AdminConfigResponse)
def get_config(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get configuration by key (Admin/Manager only)"""
    require_admin_manager(current_user)
    
    config = config_service.get_config(db, key)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found"
        )
    
    return config


@router.put("/{key}", response_model=AdminConfigResponse)
def update_config(
    key: str,
    data: AdminConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    if_match: Optional[str] = Header(None, alias="If-Match"),
):
    """Update configuration (Admin/Manager only)"""
    require_admin_manager(current_user)

    if key == "preview_strategy":
        if not isinstance(data.value_json, str) or data.value_json not in {item.value for item in PreviewStrategy}:
            allowed = ", ".join(item.value for item in PreviewStrategy)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"preview_strategy must be one of: {allowed}",
            )

    expected_version = data.version
    if if_match:
        cleaned = if_match.replace('W/', '').replace('"', '').strip()
        if cleaned.isdigit():
            header_version = int(cleaned)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="If-Match must be an integer version.",
            )
        if expected_version is not None and expected_version != header_version:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="If-Match and payload version do not match.",
            )
        expected_version = header_version

    config = config_service.update_config(db, key, data.value_json, current_user, expected_version=expected_version)
    return config
