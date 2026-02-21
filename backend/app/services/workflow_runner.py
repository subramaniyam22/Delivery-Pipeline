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
    ProjectTemplateInstance,
    Defect,
    DefectStatus,
    Notification,
    User,
    Role,
)
from app.runners.site_builder import build_and_package
from app.runners.self_review import run_self_review
from app.runners.qa_runner import run_qa, run_targeted_tests
from app.agents.defect_management_agent import DefectManagementAgent
from app.jobs.auto_assignment import run_auto_assignment
from app.services.email_service import EmailService
from app.utils.sentiment_tokens import generate_sentiment_token
from app.config import settings
from app.services import artifact_service
from app.error_codes import ErrorCode
from app.services.threshold_merge import merge_decision_policies_into_thresholds
from app.websocket.manager import manager
from app.websocket.events import WebSocketEvent
import asyncio


# Requirements match rubric weights (Content Accuracy 40%, Layout/Design 30%, Components/Functionality 30%)
REQUIREMENTS_RUBRIC_WEIGHTS = {"content_accuracy": 40, "layout_design": 30, "components_functionality": 30}


def _compute_requirements_rubric(report_json: Dict[str, Any]) -> Dict[str, Any]:
    """Compute requirements match score from build checks. Returns rubric dict and overall 0-100 score."""
    checks = report_json.get("checks") or []
    content_checks = [c for c in checks if c.get("type") in ("lighthouse",) or "seo" in (c.get("name") or "").lower()]
    layout_checks = [c for c in checks if "visual" in (c.get("type") or "").lower() or "lighthouse" in (c.get("type") or "").lower()]
    component_checks = [c for c in checks if c.get("type") == "html_validator" or "lighthouse" in (c.get("type") or "")]
    def _pct(lst):
        if not lst:
            return 100.0
        return round(100 * len([x for x in lst if x.get("passed")]) / len(lst), 2)
    content_accuracy = _pct(content_checks) if content_checks else _pct(checks)
    layout_design = _pct(layout_checks) if layout_checks else _pct(checks)
    components_functionality = _pct(component_checks) if component_checks else _pct(checks)
    overall = round(
        (content_accuracy * REQUIREMENTS_RUBRIC_WEIGHTS["content_accuracy"]
         + layout_design * REQUIREMENTS_RUBRIC_WEIGHTS["layout_design"]
         + components_functionality * REQUIREMENTS_RUBRIC_WEIGHTS["components_functionality"]) / 100,
        2,
    )
    return {
        "content_accuracy_pct": content_accuracy,
        "layout_design_pct": layout_design,
        "components_functionality_pct": components_functionality,
        "overall_rubric_score": overall,
        "weights": REQUIREMENTS_RUBRIC_WEIGHTS,
    }


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

    # Decision policies: pass_threshold_overall, qa_pass_rate_min, lighthouse_floor, axe_block_severities (Admin-editable)
    decision_policies = db.query(AdminConfig).filter(AdminConfig.key == "decision_policies_json").first()
    if decision_policies and isinstance(decision_policies.value_json, dict):
        global_thresholds = merge_decision_policies_into_thresholds(
            global_thresholds, decision_policies.value_json
        )

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
                "config_version": getattr(job, "config_version", None),
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
        default_template_id = default_template_config.value_json if default_template_config else None
        if default_template_id and not isinstance(default_template_id, UUID):
            try:
                default_template_id = UUID(str(default_template_id))
            except (ValueError, TypeError):
                default_template_id = None
        template_id = None
        if job and isinstance(job.payload_json, dict):
            raw = job.payload_json.get("template_id")
            if raw:
                try:
                    template_id = UUID(str(raw)) if not isinstance(raw, UUID) else raw
                except (ValueError, TypeError):
                    pass
        if not template_id and default_template_id:
            template_id = default_template_id

        template = None
        if template_id:
            template = db.query(TemplateRegistry).filter(TemplateRegistry.id == template_id).first()
        if not template:
            _dp_cfg = db.query(AdminConfig).filter(AdminConfig.key == "decision_policies_json").first()
            dp = _dp_cfg.value_json if _dp_cfg and isinstance(_dp_cfg.value_json, dict) else {}
            require_confirmation = dp.get("fallback_template_requires_confirmation", True)
            instance = db.query(ProjectTemplateInstance).filter(ProjectTemplateInstance.project_id == project_id).first()
            if require_confirmation and instance and not instance.fallback_confirmed_at:
                return {
                    "status": StageStatus.FAILED,
                    "summary": "Template missing; client must confirm fallback template",
                    "stage": stage.value,
                    "project_id": str(project.id),
                    "error_code": ErrorCode.TEMPLATE_FALLBACK_PENDING.value,
                }
            fallback_id = None
            if instance and instance.fallback_confirmed_at and instance.fallback_template_id:
                fallback_id = instance.fallback_template_id
            elif default_template_id:
                fallback_id = default_template_id
            if fallback_id:
                template = db.query(TemplateRegistry).filter(TemplateRegistry.id == fallback_id).first()
            if not template:
                return {
                    "status": StageStatus.FAILED,
                    "summary": "Template not configured",
                    "stage": stage.value,
                    "project_id": str(project.id),
                    "error_code": ErrorCode.TEMPLATE_MISSING.value,
                }
            if instance and (instance.fallback_confirmed_at or not require_confirmation):
                instance.use_fallback_callout = True
                if not instance.fallback_template_id:
                    instance.fallback_template_id = fallback_id
                if not instance.fallback_confirmed_at and not require_confirmation:
                    from datetime import datetime
                    instance.fallback_confirmed_at = datetime.utcnow()
                db.commit()
        # template is set below

        assets = db.query(Artifact).filter(
            Artifact.project_id == project.id,
            Artifact.stage == Stage.BUILD
        ).all()
        mapping_plan = job.payload_json.get("mapping_plan_json") if job and isinstance(job.payload_json, dict) else None
        required_score = thresholds.get("build_pass_score", 98)
        decision_policies = db.query(AdminConfig).filter(AdminConfig.key == "decision_policies_json").first()
        dp = decision_policies.value_json if decision_policies and isinstance(decision_policies.value_json, dict) else {}
        max_autofix_attempts = int(dp.get("build_autofix_retries", 3))
        score = 0.0
        report_json = {}
        evidence_links = []
        build_result = {}

        for attempt in range(1, max_autofix_attempts + 1):
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
            if score >= required_score:
                break
            if attempt < max_autofix_attempts:
                db.add(
                    AuditLog(
                        project_id=project.id,
                        actor_user_id=audit_actor_id,
                        action="BUILD_AUTOFIX_RETRY",
                        payload_json={
                            "attempt": attempt,
                            "max_attempts": max_autofix_attempts,
                            "score": score,
                            "required_score": required_score,
                        },
                    )
                )
                db.commit()

        rubric = _compute_requirements_rubric(report_json)
        report_json["requirements_rubric"] = rubric

        if score < required_score:
            from app.pipeline.state_machine import set_project_needs_review
            set_project_needs_review(
                db, project.id,
                reason=f"Build did not meet score after {max_autofix_attempts} attempts (score={score}, required={required_score}).",
                metadata={"job_id": str(job_id), "score": score, "required_score": required_score},
                actor_user_id=audit_actor_id,
            )
            output = StageOutput(
                project_id=project.id,
                job_run_id=job_id,
                stage=stage,
                status=StageStatus.FAILED,
                summary=f"Build score {score} below {required_score} after {max_autofix_attempts} attempts",
                score=score,
                report_json=report_json,
                evidence_links_json=evidence_links,
                structured_output_json={
                    "request_id": request_id,
                    "payload": payload or {},
                    "thresholds": thresholds,
                    "autofix_attempts": max_autofix_attempts,
                    "config_version": getattr(job, "config_version", None),
                },
                required_next_inputs_json=[],
            )
            db.add(output)
            db.commit()
            return {
                "status": StageStatus.FAILED,
                "summary": output.summary,
                "stage": stage.value,
                "project_id": str(project.id),
                "score": score,
                "error_code": ErrorCode.BUILD_VALIDATION_FAILED.value,
            }

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
                    "config_version": getattr(job, "config_version", None),
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
                "config_version": getattr(job, "config_version", None),
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
                "error_code": ErrorCode.BUILD_VALIDATION_FAILED.value,
            }
        qa_result = run_qa(
            db=db,
            project=project,
            preview_url=preview_url,
            thresholds=thresholds,
            uploaded_by_user_id=audit_actor_id,
        )
        decision_policies = db.query(AdminConfig).filter(AdminConfig.key == "decision_policies_json").first()
        dp = decision_policies.value_json if decision_policies and isinstance(decision_policies.value_json, dict) else {}
        qa_pass_score = thresholds.get("qa_pass_score", 98)
        qa_coverage_min = int(dp.get("qa_coverage_min", 95))
        qa_stability_min = int(dp.get("qa_stability_flake_free_min", 99))
        qa_defect_density_max = float(dp.get("qa_defect_density_critical_per_1k_loc_max", 0.5))
        report = qa_result.get("report_json") or {}
        coverage_pct = report.get("coverage_pct") if report.get("coverage_pct") is not None else qa_result.get("score")
        stability_pct = report.get("stability_pct") if report.get("stability_pct") is not None else 100.0
        defect_density = report.get("defect_density_critical_per_1k_loc")
        if defect_density is None and qa_result.get("failed_results"):
            report["defect_density_critical_per_1k_loc"] = 0.0
            defect_density = 0.0
        qa_passed = (
            qa_result["score"] >= qa_pass_score
            and (coverage_pct is None or coverage_pct >= qa_coverage_min)
            and (stability_pct is None or stability_pct >= qa_stability_min)
            and (defect_density is None or defect_density <= qa_defect_density_max)
        )
        if report.get("coverage_pct") is None:
            report["coverage_pct"] = qa_result.get("score")
        if report.get("stability_pct") is None:
            report["stability_pct"] = 99.0
        qa_result["report_json"] = report

        output = StageOutput(
            project_id=project.id,
            job_run_id=job_id,
            stage=stage,
            status=StageStatus.SUCCESS if qa_passed else StageStatus.FAILED,
            summary=summary,
            score=qa_result["score"],
            report_json=qa_result["report_json"],
            evidence_links_json=qa_result["evidence_links"],
            structured_output_json={
                "request_id": request_id,
                "payload": payload or {},
                "thresholds": thresholds,
                "config_version": getattr(job, "config_version", None),
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
                "config_version": getattr(job, "config_version", None),
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
                "config_version": getattr(job, "config_version", None),
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
                "config_version": getattr(job, "config_version", None),
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
                can_advance = True
                if validation_summary["valid"] > 0:
                    next_stage = Stage.BUILD
                    # Increment defect cycle on rework (success path); enforce cap
                    from app.services.pipeline_orchestrator import _get_defect_cycle_cap
                    from app.pipeline.state_machine import set_project_needs_review
                    project.defect_cycle_count = (project.defect_cycle_count or 0) + 1
                    cap = _get_defect_cycle_cap(db)
                    if project.defect_cycle_count > cap:
                        set_project_needs_review(
                            db, project.id,
                            reason=f"Defect cycle cap ({cap}) reached. Requires admin review.",
                            metadata={"stage": stage.value, "job_id": str(job_id), "defect_cycle_count": project.defect_cycle_count},
                            actor_user_id=audit_actor_id,
                        )
                        next_stage = None
                        can_advance = False
                elif validation_summary["validated"] > 0 and validation_summary["invalid"] == validation_summary["validated"]:
                    next_stage = Stage.COMPLETE
                else:
                    next_stage = Stage.TEST

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
                from app.pipeline.state_machine import transition_project_stage
                transition_project_stage(
                    db, project_id,
                    from_stage=project.current_stage,
                    to_stage=next_stage,
                    reason="stage_complete",
                    metadata={"job_id": str(job_id), "request_id": request_id},
                    actor_user_id=audit_actor_id,
                )
                db.refresh(project)
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
                action="JOB_ENQUEUED",
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
