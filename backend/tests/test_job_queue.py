from datetime import datetime

from app.jobs.queue import claim_next_job, enqueue_job, mark_failed, mark_running, mark_success
from app.models import JobRun, JobRunStatus, Project, ProjectStatus, Stage


def _create_project(db_session, admin_user):
    project = Project(
        title="Queue Test",
        description="Queue test project",
        client_name="Test Client",
        priority="MEDIUM",
        status=ProjectStatus.ACTIVE,
        current_stage=Stage.ONBOARDING,
        created_by_user_id=admin_user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_job_queue_success_flow(db_session, admin_user):
    project = _create_project(db_session, admin_user)
    job_id = enqueue_job(
        project_id=project.id,
        stage=Stage.ONBOARDING,
        payload_json={"foo": "bar"},
        request_id="req-1",
        actor_user_id=admin_user.id,
        db=db_session,
    )

    job = claim_next_job("worker-1", db=db_session)
    assert job is not None
    assert job.id == job_id
    assert job.locked_by == "worker-1"

    mark_running(job_id, db=db_session)
    job = db_session.query(JobRun).filter(JobRun.id == job_id).first()
    assert job.status == JobRunStatus.RUNNING
    assert job.attempts == 1

    mark_success(job_id, db=db_session)
    job = db_session.query(JobRun).filter(JobRun.id == job_id).first()
    assert job.status == JobRunStatus.SUCCESS
    assert job.finished_at is not None


def test_job_queue_retry_backoff(db_session, admin_user):
    project = _create_project(db_session, admin_user)
    job_id = enqueue_job(
        project_id=project.id,
        stage=Stage.ONBOARDING,
        payload_json={},
        request_id="req-2",
        actor_user_id=admin_user.id,
        db=db_session,
        max_attempts=3,
    )

    job = claim_next_job("worker-2", db=db_session)
    assert job is not None
    mark_running(job_id, db=db_session)

    before = datetime.utcnow()
    mark_failed(job_id, error_json={"error": "boom"}, retryable=True, db=db_session)
    job = db_session.query(JobRun).filter(JobRun.id == job_id).first()
    assert job.status == JobRunStatus.QUEUED
    assert job.next_run_at > before
    assert job.finished_at is None
