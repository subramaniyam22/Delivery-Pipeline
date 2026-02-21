from sqlalchemy.orm import Session
from app.models import AdminConfig, AuditLog
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status


# Default configuration templates
DEFAULT_CONFIGS = {
    "onboarding_template": {
        "fields": [
            {"name": "project_scope", "type": "text", "required": True},
            {"name": "client_requirements", "type": "text", "required": True},
            {"name": "timeline", "type": "text", "required": False},
            {"name": "budget", "type": "text", "required": False}
        ]
    },
    "assignment_template": {
        "task_categories": ["Development", "Testing", "Documentation", "Deployment"],
        "default_priority": "MEDIUM"
    },
    "build_checklist_template": {
        "items": [
            "Code review completed",
            "Unit tests passing",
            "Integration tests passing",
            "Documentation updated",
            "Deployment scripts ready"
        ]
    },
    "test_checklist_template": {
        "items": [
            "Test plan created",
            "Test cases executed",
            "Test report generated",
            "Defects logged",
            "Regression testing completed"
        ]
    },
    "defect_validation_rules": {
        "severity_thresholds": {
            "CRITICAL": "immediate_action",
            "HIGH": "priority_fix",
            "MEDIUM": "scheduled_fix",
            "LOW": "backlog"
        },
        "auto_validation": False
    },
    "prompts": {
        "onboarding": "Analyze project onboarding information for completeness",
        "assignment": "Create optimal task assignment plan",
        "build": "Assess build quality and readiness",
        "test": "Analyze test coverage and results",
        "defect_validation": "Validate defects and determine actions",
        "complete": "Generate project completion summary"
    },
    "onboarding_minimum_requirements": [
        "logo",
        "images",
        "copy_text",
        "wcag",
        "privacy_policy",
        "theme",
        "contacts"
    ],
    "global_stage_gates_json": {
        "onboarding": False,
        "assignment": False,
        "build": False,
        "test": False,
        "defect_validation": False,
        "complete": False
    },
    "global_thresholds_json": {
        "build_pass_score": 98,
        "qa_pass_score": 98,
        "lighthouse_min": {
            "performance": 0.7,
            "accessibility": 0.9,
            "seo": 0.9,
            "best_practices": 0.8
        },
        "lighthouse": {
            "performance_min": 0.6,
            "accessibility_min": 0.9,
            "best_practices_min": 0.8,
            "seo_min": 0.8
        },
        "axe": {
            "critical_max": 0,
            "serious_max": 0,
            "moderate_max": 5
        },
        "axe_max_critical": 0,
        "content": {
            "require_home": True,
            "require_cta": True,
            "require_contact_or_lead": True,
            "require_mobile_meta": True
        },
        "timeouts": {
            "lighthouse_sec": 120,
            "axe_sec": 60
        },
        "stage_timeouts_minutes": {
            "build": 30,
            "test": 15,
            "defect_validation": 10,
            "complete": 5
        }
    },
    "preview_strategy": "zip_only",
    "default_template_id": None,
    "worker_concurrency_json": {
        "max_parallel_jobs": 2
    },
    "decision_policies_json": {
        "reminder_cadence_hours": 24,
        "max_reminders": 10,
        "idle_minutes": 30,
        "min_scope_percent": 80,
        "build_autofix_retries": 3,
        "defect_cycle_cap": 5,
        "allow_defaults_when_missing": False,
        "fallback_template_requires_confirmation": True,
        "axe_block_severities": ["SERIOUS", "CRITICAL"],
        "axe_callout_max": 5,
        "lighthouse_floor": {"performance": 90, "accessibility": 95, "best_practices": 90, "seo": 90},
        "lighthouse_target": {"performance": 95, "accessibility": 98, "best_practices": 95, "seo": 95},
        "pass_threshold_overall": 98,
        "requirements_rubric_weights": {"content_accuracy": 40, "layout_design": 30, "components_functionality": 30},
        "qa_pass_rate_min": 98,
        "qa_coverage_min": 95,
        "qa_stability_flake_free_min": 99,
        "qa_defect_density_critical_per_1k_loc_max": 0.5,
        "idleness_counts_toward_reminders": False,
    },
}


def seed_default_configs(db: Session) -> None:
    """Seed default configuration values"""
    for key, value_json in DEFAULT_CONFIGS.items():
        # Check if config already exists
        existing = db.query(AdminConfig).filter(AdminConfig.key == key).first()
        if not existing:
            config = AdminConfig(
                key=key,
                value_json=value_json
            )
            db.add(config)
    
    db.commit()


def get_config(db: Session, key: str) -> Optional[AdminConfig]:
    """Get configuration by key"""
    return db.query(AdminConfig).filter(AdminConfig.key == key).first()


def get_all_configs(db: Session) -> List[AdminConfig]:
    """Get all configurations"""
    return db.query(AdminConfig).all()


def update_config(db: Session, key: str, value_json: Any, user, expected_version: Optional[int] = None) -> AdminConfig:
    """Update or create configuration"""
    config = get_config(db, key)
    
    if config:
        if expected_version is not None and config.config_version != expected_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Config version mismatch.",
            )
        config.value_json = value_json
        config.updated_by_user_id = user.id
        config.updated_at = datetime.utcnow()
        config.config_version = (config.config_version or 1) + 1
    else:
        if expected_version is not None and expected_version not in (0, 1):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Config version mismatch.",
            )
        config = AdminConfig(
            key=key,
            value_json=value_json,
            updated_by_user_id=user.id,
            config_version=1,
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    db.add(
        AuditLog(
            project_id=None,
            actor_user_id=user.id,
            action="CONFIG_UPDATED",
            payload_json={"key": key, "value_json": value_json},
        )
    )
    db.commit()
    return config
