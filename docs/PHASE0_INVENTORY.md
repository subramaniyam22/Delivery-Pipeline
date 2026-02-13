# Phase 0 — Inventory (current code paths)

## Job queue / worker loop
- **Worker loop**: `backend/app/jobs/worker.py` — `_run_once(worker_id)` calls `claim_next_job(worker_id, db)`, then `run_stage(db, job)`, then `mark_success`/`mark_failed`/`mark_needs_human`.
- **Job queue (project-stage)**: `backend/app/jobs/queue.py` — `enqueue_job(project_id, stage, ...)`, `claim_next_job(worker_id)`, `mark_running`, `mark_success`, `mark_failed`, `mark_needs_human`, `cancel_job`, `list_jobs`. Uses `JobRun` model; has `locked_by`/`locked_at` but no `lock_expires_at` or idempotency_key.
- **Template blueprint jobs**: `TemplateBlueprintJob` (table `template_blueprint_jobs`) — enqueued via FastAPI `BackgroundTasks.add_task(run_blueprint_job, job.id)` from `backend/app/routers/configuration.py`. Worker is in-process (backend process), not a separate worker process for blueprint.

## Job table(s)
- **JobRun**: `backend/app/models.py` — `job_runs` table: id, project_id, stage, status (QUEUED/RUNNING/SUCCESS/FAILED/NEEDS_HUMAN/CANCELED), attempts, max_attempts, payload_json, error_json, next_run_at, locked_by, locked_at, correlation_id, created_at, started_at, finished_at.
- **TemplateBlueprintJob**: `template_blueprint_jobs` — id, template_id, status, payload_json, created_at, started_at, finished_at, error_text, result_json.
- **TemplateBlueprintRun**: `template_blueprint_runs` — source of truth for a single blueprint run (status, error_*, raw_output, blueprint_json, etc.).

## Pipeline / orchestrator
- **Orchestrator**: `backend/app/services/pipeline_orchestrator.py` — `auto_advance(db, project_id, trigger_source)`, `evaluate_stage_readiness`, `on_job_success`, `on_job_failure`. Uses `ProjectStageState`, `get_contract`, HITL resolution.
- **Triggers**: Called from `onboarding` (onboarding_updated, onboarding_saved), `projects` (assignment_updated, assignment_override, artifact_upload), `pipeline` (manual_advance, manual_resume, approval_granted), `auto_assignment` (auto_assignment).

## HITL
- **Config**: `backend/app/services/hitl_service.py` — `get_global_hitl_gates()` (AdminConfig `hitl_gates_json`), `get_project_overrides()` (ProjectConfig `hitl_overrides_json`), `resolve_gate_for_stage`, `should_require_approval`, `ensure_pending_approval`, `expire_old_pending_approvals`.
- **Models**: `Project.require_manual_review`; `ProjectConfig.hitl_overrides_json`; `StageApproval` table (n8b9c0d1e2f3).
- **Orchestrator**: Sets `row.status = "awaiting_approval"` when HITL required; `awaiting_approval_stage_key` in PipelineStatus.
- **Approval**: `backend/app/routers/pipeline.py` — `approval_granted`; `backend/app/routers/workflow.py` — HITL approve/send-back via StageOutput.

## Template registry blueprint
- **Endpoints**: `backend/app/routers/configuration.py` — `POST /api/templates/{id}/blueprint/generate`, `POST /api/templates/{id}/generate-blueprint` (legacy), `GET /api/templates/{id}/blueprint/status`, `GET /api/templates/{id}/blueprint/runs`, `GET /api/blueprint-runs/{run_id}`, `GET /api/templates/{id}/blueprint-job`.
- **Frontend**: `frontend/src/lib/api.ts` — `generateBlueprint`, `generateBlueprintRun`, `getTemplateBlueprintStatus`, `getTemplateBlueprintJob`, `getBlueprintRunDetails`. Configuration page: polls status, "Generate Blueprint" calls `generateBlueprint`, status badge and "View details".

## Stages 0–6
- **Stage enum**: `backend/app/models.py` — `Stage`: SALES, ONBOARDING, ASSIGNMENT, BUILD, TEST, DEFECT_VALIDATION, COMPLETE.
- **Stage keys**: `backend/app/pipeline/stages.py` — `STAGES`: 0_sales, 1_onboarding, 2_assignment, 3_build, 4_test, 5_defect_validation, 6_complete. `STAGE_TO_KEY`, `STAGE_KEY_TO_STAGE`, `GATES_IMPLEMENTED_KEYS`.
- **Readiness**: Evaluated in `pipeline_orchestrator.py` (evaluate_stage_readiness, contract-based). `ProjectStageState` stores status, blocked_reasons_json, required_actions_json.
