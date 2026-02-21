"""
Integration-style tests for autopilot: reminders→HOLD, defect cycle cap, transition_project_stage.
Uses test db_session; mocks email where needed.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.models import (
    AdminConfig,
    AuditLog,
    OnboardingData,
    Project,
    ProjectStatus,
    Stage,
    User,
)
from app.pipeline.state_machine import (
    set_project_hold,
    set_project_needs_review,
    transition_project_stage,
)
from app.services.pipeline_orchestrator import (
    _get_defect_cycle_cap,
    run_onboarding_reminders_and_hold,
)


def test_get_defect_cycle_cap_default(db_session):
    """Without config, cap is 5."""
    cap = _get_defect_cycle_cap(db_session)
    assert cap == 5


def test_get_defect_cycle_cap_from_config(db_session):
    """With decision_policies_json, cap is read from config."""
    db_session.add(
        AdminConfig(
            key="decision_policies_json",
            value_json={"defect_cycle_cap": 7},
        )
    )
    db_session.commit()
    cap = _get_defect_cycle_cap(db_session)
    assert cap == 7


def test_transition_project_stage_updates_stage_and_history(db_session, admin_user):
    """transition_project_stage updates current_stage and appends stage_history."""
    project = Project(
        title="T",
        client_name="C",
        created_by_user_id=admin_user.id,
        current_stage=Stage.SALES,
        status=ProjectStatus.ACTIVE,
        stage_history=[],
        phase_start_dates={},
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # Ensure ProjectStageState rows exist (pipeline_orchestrator.ensure_stage_rows)
    from app.models import ProjectStageState
    from app.pipeline.stages import STAGE_KEY_TO_ORDER
    for sk in STAGE_KEY_TO_ORDER:
        db_session.add(
            ProjectStageState(project_id=project.id, stage_key=sk, status="not_started")
        )
    db_session.commit()

    ok = transition_project_stage(
        db_session,
        project.id,
        from_stage=Stage.SALES,
        to_stage=Stage.ONBOARDING,
        reason="test",
        metadata={},
        actor_user_id=admin_user.id,
    )
    assert ok is True
    db_session.refresh(project)
    assert project.current_stage == Stage.ONBOARDING
    assert len(project.stage_history or []) == 1
    assert project.stage_history[0]["from_stage"] == "SALES"
    assert project.stage_history[0]["to_stage"] == "ONBOARDING"


def test_set_project_hold_sets_status_and_reason(db_session, admin_user):
    """set_project_hold sets status=HOLD and hold_reason."""
    project = Project(
        title="T",
        client_name="C",
        created_by_user_id=admin_user.id,
        current_stage=Stage.ONBOARDING,
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    set_project_hold(
        db_session,
        project.id,
        reason="Awaiting client response. We attempted to contact you 10 times.",
        metadata={"source": "test"},
        actor_user_id=admin_user.id,
    )
    db_session.refresh(project)
    assert project.status == ProjectStatus.HOLD
    assert "10 times" in (project.hold_reason or "")


def test_set_project_needs_review_sets_status_and_reason(db_session, admin_user):
    """set_project_needs_review sets status=NEEDS_REVIEW and needs_review_reason."""
    project = Project(
        title="T",
        client_name="C",
        created_by_user_id=admin_user.id,
        current_stage=Stage.DEFECT_VALIDATION,
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    set_project_needs_review(
        db_session,
        project.id,
        reason="Defect cycle cap (5) reached. Requires admin review.",
        metadata={"defect_cycle_count": 6},
        actor_user_id=admin_user.id,
    )
    db_session.refresh(project)
    assert project.status == ProjectStatus.NEEDS_REVIEW
    assert "Defect cycle cap" in (project.needs_review_reason or "")


@patch("app.services.pipeline_orchestrator.send_client_reminder_email")
def test_reminders_and_hold_after_max_reminders(mock_send_email, db_session, admin_user):
    """When reminder_count reaches max_reminders, project is set to HOLD."""
    project = Project(
        title="Reminder Test",
        client_name="C",
        created_by_user_id=admin_user.id,
        current_stage=Stage.ONBOARDING,
        status=ProjectStatus.ACTIVE,
        client_email_ids="client@example.com",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    ob = OnboardingData(
        project_id=project.id,
        auto_reminder_enabled=True,
        reminder_count=9,
        completion_percentage=50,
        submitted_at=None,
        last_reminder_sent=datetime.utcnow() - timedelta(hours=25),
    )
    db_session.add(ob)
    db_session.add(
        AdminConfig(
            key="decision_policies_json",
            value_json={
                "reminder_cadence_hours": 24,
                "max_reminders": 10,
                "min_scope_percent": 80,
            },
        )
    )
    db_session.commit()

    count = run_onboarding_reminders_and_hold(db_session, max_projects=30)
    assert count == 1
    mock_send_email.assert_called_once()

    db_session.refresh(project)
    db_session.refresh(ob)
    assert ob.reminder_count == 10
    assert project.status == ProjectStatus.HOLD
    assert "10 times" in (project.hold_reason or "")
