from datetime import datetime
import json
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.jobs.queue import enqueue_job
from app.models import (
    AdminConfig,
    AuditLog,
    Artifact,
    JobRun,
    Project,
    ProjectConfig,
    ProjectStatus,
    Stage,
    StageOutput,
    StageStatus,
    TemplateRegistry,
    Defect,
    DefectStatus,
    Notification,
    User,
    Role,
)
from app.services.project_service import record_stage_transition
from app.runners.site_builder import build_and_package
from app.runners.self_review import run_self_review
from app.runners.qa_runner import run_qa, run_targeted_tests
from app.agents.defect_management_agent import DefectManagementAgent
from app.jobs.auto_assignment import run_auto_assignment
from app.services.email_service import EmailService
from app.utils.sentiment_tokens import generate_sentiment_token
from app.config import settings
from app.services import artifact_service
from app.websocket.manager import manager
from app.websocket.events import WebSocketEvent
import asyncio


def _get_preview_url(db: Session, project_id: UUID) -> Optional[str]:
    artifact = db.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.artifact_type.in_(["preview_link", "preview_package"]),
    ).order_by(Artifact.created_at.desc()).first()
    if artifact:
        if isinstance(artifact.metadata_json, dict):
            url = artifact.metadata_json.get("preview_url")
            if url:
                return url
        return None
    return None


def run_stage(
    db: Session,
    project_id: UUID,
    stage: Stage,
    job_id: UUID,
    request_id: Optional[str],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Stage runner skeleton. Creates StageOutput and advances/enqueues next stage
    based on HITL gate settings.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {
            "status": StageStatus.FAILED,
            "summary": "Project not found",
            "stage": stage.value,
        }

    job = db.query(JobRun).filter(JobRun.id == job_id).first()
    actor_user_id = str(job.actor_user_id) if job and job.actor_user_id else None
    audit_actor_id = job.actor_user_id if job and job.actor_user_id else project.created_by_user_id

    stage_order = [
        Stage.SALES,
        Stage.ONBOARDING,
        Stage.ASSIGNMENT,
        Stage.BUILD,
        Stage.TEST,
        Stage.DEFECT_VALIDATION,
        Stage.COMPLETE,
    ]

    global_stage_gates = {}
    global_thresholds = {}
    global_gates_config = db.query(AdminConfig).filter(AdminConfig.key == "global_stage_gates_json").first()
    if global_gates_config and isinstance(global_gates_config.value_json, dict):
        global_stage_gates = global_gates_config.value_json
    global_thresholds_config = db.query(AdminConfig).filter(AdminConfig.key == "global_thresholds_json").first()
    if global_thresholds_config and isinstance(global_thresholds_config.value_json, dict):
        global_thresholds = global_thresholds_config.value_json

    project_config = db.query(ProjectConfig).filter(ProjectConfig.project_id == project.id).first()
    hitl_enabled = bool(project_config.hitl_enabled) if project_config else False
    stage_gates = (project_config.stage_gates_json if project_config else None) or global_stage_gates
    thresholds = (project_config.thresholds_json if project_config else None) or global_thresholds
    if not stage_gates:
        stage_gates = {s.value.lower(): False for s in stage_order}
    if not hitl_enabled:
        stage_gates = {key: False for key in stage_gates.keys()}

    stage_key = stage.value.lower()
    gate_enabled = bool(stage_gates.get(stage_key, False))

    # Auto-assignment: run assignment engine + optional AI re-rank; no StageOutput
    if stage == Stage.ASSIGNMENT:
        force = bool(payload.get("force", False)) if isinstance(payload, dict) else False
        result = run_auto_assignment(project_id, force=force, db=db)
        if result.get("status") == "error":
            return {
                "status": StageStatus.FAILED,
                "summary": result.get("error", "Auto-assignment failed"),
                "stage": stage.value,
                "project_id": str(project.id),
            }
        summary_msg = result.get("message") or "Auto-assignment completed"
        if result.get("blocked_reasons"):
            summary_msg += "; " + "; ".join(result["blocked_reasons"])
        return {
            "status": StageStatus.SUCCESS,
            "summary": summary_msg,
            "stage": stage.value,
            "project_id": str(project.id),
        }

    summary = f"Stage {stage.value} executed via job {job_id}"

    if stage != Stage.BUILD and gate_enabled:
        output = StageOutput(
            project_id=project.id,
            job_run_id=job_id,
            stage=stage,
            status=StageStatus.NEEDS_HUMAN,
            gate_decision="PAUSED_HITL",
            summary=f"{summary} (HITL gate)",
            structured_output_json={
                "placeholder": True,
                "request_id": request_id,
                "payload": payload or {},
                "thresholds": thresholds,
            },
            required_next_inputs_json=[],
        )
        db.add(output)
        db.add(
            AuditLog(
                project_id=project.id,
                actor_user_id=audit_actor_id,
                action="STAGE_HITL_PAUSED",
                payload_json={
                    "stage": stage.value,
                    "request_id": request_id,
                },
            )
        )
        db.commit()
        return {
            "status": StageStatus.NEEDS_HUMAN,
            "summary": output.summary,
            "stage": stage.value,
            "project_id": str(project.id),
        }

    if stage == Stage.BUILD:
        preview_strategy_config = db.query(AdminConfig).filter(AdminConfig.key == "preview_strategy").first()
        preview_strategy = preview_strategy_config.value_json if preview_strategy_config else "zip_only"
        default_template_config = db.query(AdminConfig).filter(AdminConfig.key == "default_template_id").first()
        template_id = None
        if job and isinstance(job.payload_json, dict):
            template_id = job.payload_json.get("template_id")
        if not template_id and default_template_config:
            template_id = default_template_config.value_json

        template = None
        if template_id:
            template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
        if not template:
            return {
                "status": StageStatus.FAILED,
                "summary": "Template not configured",
                "stage": stage.value,
                "project_id": str(project.id),
            }

        assets = db.query(Artifact).filter(
            Artifact.project_id == project.id,
            Artifact.stage == Stage.BUILD
        ).all()
        mapping_plan = job.payload_json.get("mapping_plan_json") if job and isinstance(job.payload_json, dict) else None
        build_result = build_and_package(
            db=db,
            project_id=project.id,
            stage=Stage.BUILD,
            template=template,
            assets=assets,
            mapping_plan_json=mapping_plan,
            preview_strategy=preview_strategy,
            actor_user_id=audit_actor_id,
        )

        score, report_json, evidence_links = run_self_review(
            db=db,
            project_id=project.id,
            preview_url=build_result.get("preview_url"),
            baseline_dir=build_result.get("baseline_dir"),
            thresholds=thresholds,
            actor_user_id=audit_actor_id,
        )

        if gate_enabled:
            output = StageOutput(
                project_id=project.id,
                job_run_id=job_id,
                stage=stage,
                status=StageStatus.NEEDS_HUMAN,
                gate_decision="PAUSED_HITL",
                summary=f"{summary} (HITL gate)",
                score=score,
                report_json=report_json,
                evidence_links_json=evidence_links,
                structured_output_json={
                    "request_id": request_id,
                    "payload": payload or {},
                    "thresholds": thresholds,
                },
                required_next_inputs_json=[],
            )
            db.add(output)
            db.add(
                AuditLog(
                    project_id=project.id,
                    actor_user_id=audit_actor_id,
                    action="STAGE_HITL_PAUSED",
                    payload_json={
                        "stage": stage.value,
                        "request_id": request_id,
                    },
                )
            )
            db.commit()
            return {
                "status": StageStatus.NEEDS_HUMAN,
                "summary": output.summary,
                "stage": stage.value,
                "project_id": str(project.id),
            }

        output = StageOutput(
            project_id=project.id,
            job_run_id=job_id,
            stage=stage,
            status=StageStatus.SUCCESS,
            summary=summary,
            score=score,
            report_json=report_json,
            evidence_links_json=evidence_links,
            structured_output_json={
                "request_id": request_id,
                "payload": payload or {},
                "thresholds": thresholds,
            },
            required_next_inputs_json=[],
        )
        db.add(output)
    elif stage == Stage.TEST:
        preview_url = _get_preview_url(db, project.id)
        if not preview_url:
            return {
                "status": StageStatus.FAILED,
                "summary": "Preview URL not found for QA",
                "stage": stage.value,
                "project_id": str(project.id),
            }
        qa_result = run_qa(
            db=db,
            project=project,
            preview_url=preview_url,
            thresholds=thresholds,
            uploaded_by_user_id=audit_actor_id,
        )

        output = StageOutput(
            project_id=project.id,
            job_run_id=job_id,
            stage=stage,
            status=StageStatus.SUCCESS if qa_result["score"] >= thresholds.get("qa_pass_score", 98) else StageStatus.FAILED,
            summary=summary,
            score=qa_result["score"],
            report_json=qa_result["report_json"],
            evidence_links_json=qa_result["evidence_links"],
            structured_output_json={
                "request_id": request_id,
                "payload": payload or {},
                "thresholds": thresholds,
            },
            required_next_inputs_json=[],
        )
        db.add(output)

        if qa_result["failed_results"]:
            defect_agent = DefectManagementAgent(db)
            defect_agent.create_defects_from_failed_tests(project_id=str(project.id), failed_results=qa_result["failed_results"])

    elif stage == Stage.DEFECT_VALIDATION:
        preview_url = _get_preview_url(db, project.id)
        failed_defects = db.query(Defect).filter(
            Defect.project_id == project.id,
            Defect.source_test_case_id.isnot(None),
            Defect.status.in_([DefectStatus.DRAFT, DefectStatus.FIXED]),
        ).all()

        validation_summary = {"validated": 0, "valid": 0, "invalid": 0}
        if preview_url and failed_defects:
            defect_case_ids = [str(d.source_test_case_id) for d in failed_defects if d.source_test_case_id]
            qa_result = run_targeted_tests(
                db=db,
                project=project,
                preview_url=preview_url,
                test_case_ids=defect_case_ids,
                uploaded_by_user_id=audit_actor_id,
            )
            failed_test_case_ids = set(qa_result["failed_case_ids"])
            for defect in failed_defects:
                validation_summary["validated"] += 1
                if str(defect.source_test_case_id) in failed_test_case_ids:
                    defect.status = DefectStatus.VALID
                    validation_summary["valid"] += 1
                else:
                    defect.status = DefectStatus.INVALID
                    validation_summary["invalid"] += 1
            db.commit()

        output = StageOutput(
            project_id=project.id,
            job_run_id=job_id,
            stage=stage,
            status=StageStatus.SUCCESS,
            summary=summary,
            structured_output_json={
                "request_id": request_id,
                "payload": payload or {},
                "thresholds": thresholds,
                "validation_summary": validation_summary,
            },
            required_next_inputs_json=[],
        )
        db.add(output)

    elif stage == Stage.COMPLETE:
        preview_url = _get_preview_url(db, project.id)
        sentiment_token = generate_sentiment_token(project.id)
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        sentiment_link = f"{frontend_url}/sentiment/{sentiment_token}"
        report_json = {
            "project": project.title,
            "preview_url": preview_url,
            "sentiment_link": sentiment_link,
        }
        artifact = artifact_service.create_artifact_from_bytes(
            db=db,
            project_id=project.id,
            stage=stage,
            filename=f"completion-report-{project.id}.json",
            content=json.dumps(report_json, indent=2).encode("utf-8"),
            artifact_type="completion_report",
            uploaded_by_user_id=audit_actor_id,
            metadata_json={},
        )
        output = StageOutput(
            project_id=project.id,
            job_run_id=job_id,
            stage=stage,
            status=StageStatus.SUCCESS,
            summary=summary,
            report_json=report_json,
            evidence_links_json=[artifact.url],
            structured_output_json={
                "request_id": request_id,
                "payload": payload or {},
            },
            required_next_inputs_json=[],
        )
        db.add(output)
        client_emails = [e.strip() for e in (project.client_email_ids or "").split(",") if e.strip()]
        if client_emails:
            success, detail = EmailService.send_email_with_retry(
                to=client_emails,
                subject=f"Project Complete: {project.title}",
                html_content=f"<p>Your project is complete.</p><p>Preview: {preview_url}</p><p>Sentiment: {sentiment_link}</p>",
                return_details=True,
            )
            report_json["email_status"] = "SENT" if success else "FAILED"
            output.report_json = report_json
            if not success:
                db.add(
                    AuditLog(
                        project_id=project.id,
                        actor_user_id=audit_actor_id,
                        action="EMAIL_SEND_FAILED",
                        payload_json={"error": detail, "recipients": client_emails},
                    )
                )
                admins = db.query(User).filter(User.role.in_([Role.ADMIN, Role.MANAGER])).all()
                for admin in admins:
                    db.add(
                        Notification(
                            user_id=admin.id,
                            project_id=project.id,
                            type="EMAIL_FAILED",
                            message=f"Completion email failed for {project.title}.",
                            is_read=False,
                        )
                    )
            else:
                db.add(
                    AuditLog(
                        project_id=project.id,
                        actor_user_id=audit_actor_id,
                        action="EMAIL_SENT",
                        payload_json={"recipients": client_emails},
                    )
                )
            db.commit()
        admins = db.query(User).filter(User.role.in_([Role.ADMIN, Role.MANAGER])).all()
        for admin in admins:
            notification = Notification(
                user_id=admin.id,
                project_id=project.id,
                type="PROJECT_COMPLETE",
                message=f"Project completed: {project.title}",
                is_read=False,
            )
            db.add(notification)
            db.commit()
            event = WebSocketEvent.notification(notification.message, level="success", user_id=str(admin.id))
            try:
                asyncio.run(manager.send_personal_message(event, str(admin.id)))
            except Exception:
                pass
    else:
        output = StageOutput(
            project_id=project.id,
            job_run_id=job_id,
            stage=stage,
            status=StageStatus.SUCCESS,
            summary=summary,
            structured_output_json={
                "placeholder": True,
                "request_id": request_id,
                "payload": payload or {},
                "thresholds": thresholds,
            },
            required_next_inputs_json=[],
        )
        db.add(output)

    next_stage = None
    if stage in stage_order and project.current_stage == stage:
        current_idx = stage_order.index(stage)
        if current_idx < len(stage_order) - 1:
            can_advance = True
            if stage == Stage.BUILD:
                required_score = thresholds.get("build_pass_score", 98)
                can_advance = output.score is not None and output.score >= required_score
            if stage == Stage.TEST:
                required_score = thresholds.get("qa_pass_score", 98)
                can_advance = output.score is not None and output.score >= required_score
                if output.status == StageStatus.FAILED:
                    can_advance = True
                    next_stage = Stage.DEFECT_VALIDATION
            if stage == Stage.DEFECT_VALIDATION:
                if validation_summary["valid"] > 0:
                    next_stage = Stage.BUILD
                elif validation_summary["validated"] > 0 and validation_summary["invalid"] == validation_summary["validated"]:
                    next_stage = Stage.COMPLETE
                else:
                    next_stage = Stage.TEST
                can_advance = True

            if can_advance and not next_stage:
                next_stage = stage_order[current_idx + 1]

            # Do not advance from ONBOARDING to ASSIGNMENT until client has submitted onboarding
            if stage == Stage.ONBOARDING and next_stage == Stage.ASSIGNMENT:
                from app.models import OnboardingData
                ob = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
                if not ob or not getattr(ob, "submitted_at", None):
                    can_advance = False
                    next_stage = None

            if can_advance and next_stage:
                previous_stage = project.current_stage
                project.current_stage = next_stage
                project.status = ProjectStatus.ACTIVE
                record_stage_transition(
                    project,
                    previous_stage,
                    project.current_stage,
                    actor_user_id=actor_user_id,
                    request_id=request_id,
                )
    elif stage == Stage.SALES and project.current_stage == Stage.SALES:
        project.status = ProjectStatus.ACTIVE

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)

    if next_stage:
        enqueue_job(
            project_id=project.id,
            stage=next_stage,
            payload_json={"triggered_by": stage.value},
            request_id=request_id,
            actor_user_id=audit_actor_id,
            db=db,
        )
        db.add(
            AuditLog(
                project_id=project.id,
                actor_user_id=audit_actor_id,
                action="STAGE_TRANSITION",
                payload_json={
                    "from_stage": stage.value,
                    "to_stage": next_stage.value,
                    "request_id": request_id,
                },
            )
        )
        db.commit()

    return {
        "status": StageStatus.SUCCESS,
        "summary": summary,
        "stage": stage.value,
        "project_id": str(project.id),
    }
