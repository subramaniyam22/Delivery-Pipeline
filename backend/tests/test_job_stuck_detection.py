from datetime import datetime, timedelta

from app.models import AdminConfig, JobRun, JobRunStatus, Project, Stage


def test_stuck_jobs_endpoint_flags_long_running(client, db_session, admin_user, auth_headers):
    db_session.add(
        AdminConfig(
            key="global_thresholds_json",
            value_json={"stage_timeouts_minutes": {"build": 1}},
            updated_by_user_id=admin_user.id,
        )
    )
    project = Project(
        title="Test Project",
        client_name="Client",
        created_by_user_id=admin_user.id,
        current_stage=Stage.BUILD,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    job = JobRun(
        project_id=project.id,
        stage=Stage.BUILD,
        status=JobRunStatus.RUNNING,
        attempts=1,
        max_attempts=3,
        started_at=datetime.utcnow() - timedelta(minutes=5),
        next_run_at=datetime.utcnow(),
    )
    db_session.add(job)
    db_session.commit()

    response = client.get("/admin/jobs/stuck", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == str(job.id) for item in payload)
