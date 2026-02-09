from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user
from app.models import JobRun, JobRunStatus, StageOutput, StageStatus, Project, User, Role, Defect, ClientSentiment, Stage

router = APIRouter(prefix="/admin/metrics", tags=["metrics"])


def _require_admin_manager(user: User) -> None:
    if user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(status_code=403, detail="Only Admin or Manager can access metrics")


@router.get("")
def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    _require_admin_manager(current_user)

    jobs_by_status = dict(
        db.query(JobRun.status, func.count(JobRun.id))
        .group_by(JobRun.status)
        .all()
    )

    avg_durations = db.query(
        JobRun.stage,
        func.avg(func.extract("epoch", JobRun.finished_at - JobRun.started_at) * 1000),
    ).filter(JobRun.started_at.isnot(None), JobRun.finished_at.isnot(None)).group_by(JobRun.stage).all()
    avg_durations_ms = {stage.value: int(duration or 0) for stage, duration in avg_durations}

    success_rates = db.query(
        JobRun.stage,
        func.sum(case((JobRun.status == JobRunStatus.SUCCESS, 1), else_=0)).label("successes"),
        func.count(JobRun.id).label("total"),
    ).group_by(JobRun.stage).all()
    success_rate_by_stage = {}
    for stage, successes, total in success_rates:
        success_rate_by_stage[stage.value] = round((successes / total) * 100, 1) if total else 0

    failure_reason_expr = func.coalesce(
        JobRun.error_json["error"].astext,
        JobRun.error_json["summary"].astext,
        JobRun.error_json["message"].astext,
        "unknown",
    )
    failure_reasons = db.query(
        failure_reason_expr,
        func.count(JobRun.id),
    ).filter(JobRun.status == JobRunStatus.FAILED).group_by(failure_reason_expr).order_by(func.count(JobRun.id).desc()).limit(5).all()

    total_outputs = db.query(func.count(StageOutput.id)).scalar() or 0
    hitl_outputs = db.query(func.count(StageOutput.id)).filter(StageOutput.status == StageStatus.NEEDS_HUMAN).scalar() or 0
    hitl_rate = round((hitl_outputs / total_outputs) * 100, 1) if total_outputs else 0

    defect_loop_count = 0
    projects = db.query(Project).all()
    for project in projects:
        history = project.stage_history or []
        for entry in history:
            if entry.get("from_stage") == "DEFECT_VALIDATION" and entry.get("to_stage") in {"BUILD", "TEST"}:
                defect_loop_count += 1

    # Quality metrics
    build_outputs = db.query(StageOutput).filter(StageOutput.stage == Stage.BUILD).all()
    build_pass = len([o for o in build_outputs if o.status == StageStatus.SUCCESS])
    build_pass_rate = round((build_pass / len(build_outputs)) * 100, 1) if build_outputs else 0

    test_outputs = db.query(StageOutput).filter(StageOutput.stage == Stage.TEST).all()
    test_pass = len([o for o in test_outputs if o.status == StageStatus.SUCCESS])
    qa_pass_rate = round((test_pass / len(test_outputs)) * 100, 1) if test_outputs else 0

    sentiments = db.query(ClientSentiment).all()
    avg_sentiment = round(sum(s.rating for s in sentiments) / len(sentiments), 2) if sentiments else 0

    defect_escape_count = 0
    completion_outputs = db.query(StageOutput).filter(StageOutput.stage == Stage.COMPLETE).all()
    completion_map = {str(o.project_id): o.created_at for o in completion_outputs}
    defects = db.query(Defect).all()
    for defect in defects:
        completed_at = completion_map.get(str(defect.project_id))
        if completed_at and defect.created_at > completed_at:
            defect_escape_count += 1

    return {
        "jobs_by_status": {k.value if hasattr(k, "value") else str(k): v for k, v in jobs_by_status.items()},
        "avg_durations_ms": avg_durations_ms,
        "success_rate_by_stage": success_rate_by_stage,
        "failure_reasons_top": [{"reason": reason, "count": count} for reason, count in failure_reasons],
        "hitl_rate": hitl_rate,
        "defect_loop_count": defect_loop_count,
        "quality_metrics": {
            "self_review_pass_rate": build_pass_rate,
            "qa_pass_rate": qa_pass_rate,
            "defect_escape_count": defect_escape_count,
            "avg_client_sentiment": avg_sentiment,
        },
    }
