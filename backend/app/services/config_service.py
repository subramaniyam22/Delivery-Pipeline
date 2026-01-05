from sqlalchemy.orm import Session
from app.models import AdminConfig
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


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
    }
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


def update_config(db: Session, key: str, value_json: Dict[str, Any], user) -> AdminConfig:
    """Update or create configuration"""
    config = get_config(db, key)
    
    if config:
        config.value_json = value_json
        config.updated_by_user_id = user.id
        config.updated_at = datetime.utcnow()
    else:
        config = AdminConfig(
            key=key,
            value_json=value_json,
            updated_by_user_id=user.id
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    return config
