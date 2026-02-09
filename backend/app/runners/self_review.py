import csv
import io
import json
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.agents.prompts import get_llm
from app.utils.llm import invoke_llm
from app.utils.llm_cache import get_cached_plan, set_cached_plan
from app.models import Artifact, Stage
from app.runners.html_validator import validate_html
from app.runners.lighthouse_runner import run_lighthouse
from app.runners.visual_regression import run_visual_regression
from app.services import artifact_service


def _parse_checklist(content: bytes, filename: str) -> List[Dict[str, Any]]:
    if filename.lower().endswith(".json"):
        return json.loads(content.decode("utf-8"))
    if filename.lower().endswith(".csv"):
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader]
    raise ValueError("Unsupported checklist format")


def _generate_plan_with_llm(project_id: str, requirements: Dict[str, Any], assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cached = get_cached_plan(project_id, "build", requirements, assets)
    if cached and isinstance(cached, list):
        return cached
    llm = get_llm(task="checklist")
    prompt = (
        "Generate a deterministic checklist plan JSON for website build review. "
        "Return a JSON array of checks with fields: name, type, target. "
        f"Requirements: {json.dumps(requirements)}"
    )
    try:
        response = invoke_llm(llm, prompt)
        if isinstance(response, str):
            plan = json.loads(response)
            if isinstance(plan, list):
                set_cached_plan(project_id, "build", requirements, assets, plan)
                return plan
    except Exception:
        pass
    return [
        {"name": "html_validation", "type": "html_validator", "target": "homepage"},
        {"name": "lighthouse", "type": "lighthouse", "target": "homepage"},
        {"name": "visual_regression", "type": "visual_regression", "target": "homepage"},
    ]


def _score_checks(checks: List[Dict[str, Any]]) -> float:
    if not checks:
        return 0.0
    passed = len([c for c in checks if c.get("passed")])
    return round(100 * (passed / len(checks)), 2)


def run_self_review(
    db: Session,
    project_id,
    preview_url: Optional[str],
    baseline_dir: Optional[str],
    thresholds: Dict[str, Any],
    actor_user_id,
) -> Tuple[float, Dict[str, Any], List[str]]:
    checks: List[Dict[str, Any]] = []
    evidence_links: List[str] = []

    checklist = None
    checklist_artifact = (
        db.query(Artifact)
        .filter(Artifact.project_id == project_id, Artifact.artifact_type == "checklist_build")
        .order_by(Artifact.created_at.desc())
        .first()
    )
    if checklist_artifact:
        content = artifact_service.get_artifact_bytes(checklist_artifact)
        checklist = _parse_checklist(content, checklist_artifact.filename)
    else:
        checklist = _generate_plan_with_llm(str(project_id), {"preview_url": preview_url}, [])

    if preview_url:
        types_to_run = {entry.get("type", "") for entry in checklist or []}
        if not types_to_run:
            types_to_run = {"html_validator", "lighthouse", "visual_regression"}

        if "html_validator" in types_to_run:
            checks.extend(validate_html(preview_url))

        with tempfile.TemporaryDirectory() as workdir:
            if "lighthouse" in types_to_run:
                lighthouse_checks, report = run_lighthouse(preview_url, workdir, thresholds)
                checks.extend(lighthouse_checks)
                if report:
                    report_bytes = json.dumps(report, indent=2).encode("utf-8")
                    artifact = artifact_service.create_artifact_from_bytes(
                        db=db,
                        project_id=project_id,
                        stage=Stage.BUILD,
                        filename="lighthouse-report.json",
                        content=report_bytes,
                        artifact_type="lighthouse_report",
                        uploaded_by_user_id=actor_user_id,
                    )
                    evidence_links.append(artifact.url)

            if "visual_regression" in types_to_run:
                visual_checks, screenshot_path, diff_path = run_visual_regression(preview_url, baseline_dir, workdir)
                checks.extend(visual_checks)
                if screenshot_path:
                    with open(screenshot_path, "rb") as handle:
                        screenshot_bytes = handle.read()
                    artifact = artifact_service.create_artifact_from_bytes(
                        db=db,
                        project_id=project_id,
                        stage=Stage.BUILD,
                        filename="preview-screenshot.png",
                        content=screenshot_bytes,
                        artifact_type="screenshots",
                        uploaded_by_user_id=actor_user_id,
                    )
                    evidence_links.append(artifact.url)
                if diff_path:
                    with open(diff_path, "rb") as handle:
                        diff_bytes = handle.read()
                    artifact = artifact_service.create_artifact_from_bytes(
                        db=db,
                        project_id=project_id,
                        stage=Stage.BUILD,
                        filename="visual-diff.png",
                        content=diff_bytes,
                        artifact_type="visual_diff",
                        uploaded_by_user_id=actor_user_id,
                    )
                    evidence_links.append(artifact.url)

    score = _score_checks(checks)
    report_json = {
        "summary": f"Self review score {score}",
        "checks": checks,
        "checklist_used": checklist,
    }
    artifact = artifact_service.create_artifact_from_bytes(
        db=db,
        project_id=project_id,
        stage=Stage.BUILD,
        filename="self-review-report.json",
        content=json.dumps(report_json, indent=2).encode("utf-8"),
        artifact_type="self_review_report",
        uploaded_by_user_id=actor_user_id,
    )
    evidence_links.append(artifact.url)
    return score, report_json, evidence_links
