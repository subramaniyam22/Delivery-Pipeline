from uuid import uuid4
from datetime import datetime

from app.models import (
    Project,
    ProjectStatus,
    Stage,
    JobRun,
    JobRunStatus,
    Artifact,
    Defect,
    DefectSeverity,
    DefectStatus,
    TestScenario,
    TestCase,
    TestExecution,
    TestExecutionStatus,
)
from app.utils.sentiment_tokens import generate_sentiment_token, verify_sentiment_token
from app.runners.qa_runner import validate_qa_output_schema
from app.services import workflow_runner


def _create_project(db, user_id):
    project = Project(
        title="QA Project",
        client_name="Client",
        status=ProjectStatus.ACTIVE,
        current_stage=Stage.DEFECT_VALIDATION,
        created_by_user_id=user_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_sentiment_token_verify_and_expiry():
    project_id = uuid4()
    token = generate_sentiment_token(project_id)
    assert verify_sentiment_token(token) == str(project_id)

    expired = generate_sentiment_token(project_id, ttl_hours=0)
    assert verify_sentiment_token(expired) is None


def test_defect_validation_routing(db_session, admin_user, monkeypatch):
    project = _create_project(db_session, admin_user.id)

    job = JobRun(
        project_id=project.id,
        stage=Stage.DEFECT_VALIDATION,
        status=JobRunStatus.QUEUED,
        attempts=0,
        max_attempts=1,
        payload_json={},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    artifact = Artifact(
        project_id=project.id,
        stage=Stage.BUILD,
        type="preview",
        artifact_type="preview_link",
        filename="preview.txt",
        url="preview.txt",
        uploaded_by_user_id=admin_user.id,
        metadata_json={"preview_url": "http://example.com"},
    )
    db_session.add(artifact)
    db_session.commit()

    scenario = TestScenario(project_id=project.id, name="Scenario", is_auto_generated=True)
    db_session.add(scenario)
    db_session.commit()
    db_session.refresh(scenario)

    test_case = TestCase(scenario_id=scenario.id, title="Case", is_automated=True)
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

    execution = TestExecution(
        project_id=project.id,
        name="Exec",
        status=TestExecutionStatus.COMPLETED,
        executed_by="QA",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)

    defect = Defect(
        project_id=project.id,
        title="Fail",
        severity=DefectSeverity.HIGH,
        status=DefectStatus.DRAFT,
        description="Failed test",
        source_test_case_id=test_case.id,
    )
    db_session.add(defect)
    db_session.commit()

    def fake_run_targeted_tests(*args, **kwargs):
        return {
            "report_json": {},
            "failed_case_ids": [str(test_case.id)],
        }

    monkeypatch.setattr(workflow_runner, "run_targeted_tests", fake_run_targeted_tests)
    result = workflow_runner.run_stage(
        db=db_session,
        project_id=project.id,
        stage=Stage.DEFECT_VALIDATION,
        job_id=job.id,
        request_id="test",
        payload={},
    )

    db_session.refresh(project)
    db_session.refresh(defect)
    assert str(result["status"]) in ["SUCCESS", "StageStatus.SUCCESS"]
    assert defect.status == DefectStatus.VALID
    assert project.current_stage == Stage.BUILD


def test_qa_output_schema_validation():
    output = {
        "score": 100,
        "report_json": {},
        "evidence_links": [],
        "failed_results": [],
        "axe_ok": True,
    }
    assert validate_qa_output_schema(output) is True
