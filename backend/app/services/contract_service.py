"""
Delivery Contract service: build from sources, get/update/patch, keep in sync.
Contract is the canonical project spec for agents and autopilot.
"""
from __future__ import annotations

import copy
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.schema_v1 import empty_contract, stages_skeleton, SCHEMA_VERSION
from app.models import (
    Artifact,
    OnboardingData,
    Project,
    ProjectContract,
    ProjectStageState,
    StageApproval,
    StageOutput,
)
from app.pipeline.stages import STAGE_TO_KEY

logger = logging.getLogger(__name__)


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge patch into base. Patch wins; lists are replaced (not merged)."""
    result = copy.deepcopy(base)
    for k, v in patch.items():
        if k not in result:
            result[k] = copy.deepcopy(v)
        elif isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = copy.deepcopy(v)
    return result


def build_contract_from_sources(db: Session, project_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Build full contract_json from onboarding, project, artifacts, stage states, approvals, stage outputs.
    Returns None on failure (caller should not crash pipeline).
    """
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        now = datetime.utcnow()
        updated_at_str = now.isoformat() + "Z"
        c = empty_contract(str(project_id), "system", updated_at_str)
        c["meta"]["updated_at"] = updated_at_str

        # Onboarding
        ob = db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
        if ob:
            contacts = list(ob.contacts_json or [])
            primary = next((x for x in contacts if x.get("is_primary")), contacts[0] if contacts else {})
            c["onboarding"] = {
                "status": "submitted" if ob.submitted_at else "draft",
                "summary": (ob.requirements_json or {}).get("summary", "") if isinstance(ob.requirements_json, dict) else "",
                "primary_contact": primary if isinstance(primary, dict) else {},
                "brand": {
                    "logo_url": ob.logo_url,
                    "logo_file_path": ob.logo_file_path,
                    "images": list(ob.images_json or []),
                },
                "design_preferences": {
                    "theme_preference": ob.theme_preference,
                    "theme_colors": dict(ob.theme_colors_json or {}),
                },
                "compliance": {
                    "wcag_required": bool(ob.wcag_compliance_required),
                    "wcag_level": ob.wcag_level or "AA",
                    "wcag_confirmed": bool(ob.wcag_confirmed),
                },
                "website_fundamentals": {
                    "copy_text": ob.copy_text,
                    "privacy_policy_url": ob.privacy_policy_url,
                },
            }
        c["onboarding"]["updated_at"] = ob.updated_at.isoformat() if ob and ob.updated_at else None

        # Assignments
        c["assignments"] = {
            "consultant_id": str(project.consultant_user_id) if project.consultant_user_id else None,
            "builder_id": str(project.builder_user_id) if project.builder_user_id else None,
            "tester_id": str(project.tester_user_id) if project.tester_user_id else None,
        }

        # Template
        tid = None
        tver = None
        if ob:
            tid = ob.selected_template_id or ob.theme_preference
            tver = 1
        c["template"] = {
            "selected_template_id": tid,
            "selected_template_version": tver,
            "blueprint_ref": f"{tid}:{tver}" if tid else None,
        }

        # Artifacts
        artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).all()
        uploads: List[Dict[str, Any]] = []
        build_outputs: Dict[str, Optional[str]] = {"preview_url": None, "repo_url": None, "bundle_url": None}
        for a in artifacts:
            uploads.append({
                "id": str(a.id),
                "type": (a.artifact_type or a.type or "doc").lower().replace(" ", "_"),
                "url": a.url or "",
                "updated_at": a.created_at.isoformat() if a.created_at else None,
            })
            if (a.artifact_type or "").lower() in ("preview_link", "preview_url") and a.metadata_json:
                url = (a.metadata_json or {}).get("preview_url") if isinstance(a.metadata_json, dict) else None
                if url:
                    build_outputs["preview_url"] = url
        c["artifacts"] = {"uploads": uploads, "build_outputs": build_outputs}

        # Stages (from project_stage_state + latest stage_outputs)
        c["stages"] = stages_skeleton()
        rows = db.query(ProjectStageState).filter(ProjectStageState.project_id == project_id).all()
        for r in rows:
            if r.stage_key in c["stages"]:
                c["stages"][r.stage_key]["status"] = r.status or "not_started"
                c["stages"][r.stage_key]["blocked_reasons"] = list(r.blocked_reasons_json or [])
                c["stages"][r.stage_key]["outputs"] = {}
        outputs = db.query(StageOutput).filter(StageOutput.project_id == project_id).order_by(StageOutput.created_at.desc()).all()
        for o in outputs:
            stage_key = STAGE_TO_KEY.get(o.stage)
            if stage_key and stage_key in c["stages"]:
                out = c["stages"][stage_key].get("outputs") or {}
                if not out:
                    out = {
                        "score": o.score,
                        "report_json": dict(o.report_json or {}),
                        "structured_output_json": dict(o.structured_output_json or {}),
                    }
                    c["stages"][stage_key]["outputs"] = out

        # Quality (from latest stage outputs or placeholder)
        c["quality"] = {
            "lighthouse": {"perf": None, "a11y": None, "seo": None, "bp": None},
            "axe": {"critical": None, "serious": None},
        }
        for o in outputs:
            rj = o.report_json or {}
            if isinstance(rj, dict):
                if "lighthouse" in rj:
                    c["quality"]["lighthouse"].update({k: rj["lighthouse"].get(k) for k in c["quality"]["lighthouse"] if isinstance(rj["lighthouse"], dict)})
                if "accessibility" in rj:
                    c["quality"]["lighthouse"]["a11y"] = rj.get("accessibility")

        # Approvals
        approvals = db.query(StageApproval).filter(StageApproval.project_id == project_id).order_by(StageApproval.updated_at.desc()).all()
        c["approvals"] = [
            {"stage_key": a.stage_key, "status": a.status, "updated_at": a.updated_at.isoformat() if a.updated_at else None}
            for a in approvals[:50]
        ]

        # Audit (append-only in meta)
        c["meta"]["audit"] = c.get("audit", []) or []
        return c
    except Exception as e:
        logger.exception("Contract build failed for project %s: %s", project_id, e)
        return None


def create_or_update_contract(db: Session, project_id: UUID, source: str = "system") -> Optional[Dict[str, Any]]:
    """
    Build contract from sources; insert (version=1) or update (increment version), append audit.
    Clears project.contract_build_error on success; sets it on failure.
    Returns contract_json or None.
    """
    contract_json = build_contract_from_sources(db, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
    if contract_json is None:
        project.contract_build_error = "Contract build failed (see logs)"
        db.commit()
        return None
    project.contract_build_error = None
    now = datetime.utcnow()
    updated_at_str = now.isoformat() + "Z"
    contract_json["meta"]["updated_at"] = updated_at_str
    contract_json["meta"]["last_updated_by"] = source

    row = db.query(ProjectContract).filter(ProjectContract.project_id == project_id).first()
    audit_entry = {"at": updated_at_str, "event": "contract_updated", "by": source}
    if not row:
        contract_json["meta"]["audit"] = [{"at": updated_at_str, "event": "contract_created", "by": source}]
        row = ProjectContract(
            project_id=project_id,
            contract_json=contract_json,
            version=1,
            updated_at=now,
            created_at=now,
        )
        db.add(row)
    else:
        contract_json["meta"]["audit"] = list(row.contract_json.get("meta", {}).get("audit", [])) + [audit_entry]
        row.contract_json = contract_json
        row.version = (row.version or 1) + 1
        row.updated_at = now
    # Invalidate client preview when contract changes so it regenerates with new data
    project = db.query(Project).filter(Project.id == project_id).first()
    if project and hasattr(project, "client_preview_status"):
        project.client_preview_status = "not_generated"
        project.client_preview_hash = None
    db.commit()
    db.refresh(row)
    return row.contract_json


def get_contract(db: Session, project_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Return contract_json for project. Lazy init: if no row, build and create.
    Returns None only if build fails.
    """
    row = db.query(ProjectContract).filter(ProjectContract.project_id == project_id).first()
    if row:
        return row.contract_json
    # Lazy init
    created = create_or_update_contract(db, project_id, source="system")
    return created


def patch_contract(
    db: Session,
    project_id: UUID,
    patch_json: Dict[str, Any],
    source: str,
    expected_version: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Deep-merge patch into contract; increment version and append audit.
    If expected_version is set and current version != expected_version, reject (return None) for conflict.
    """
    row = db.query(ProjectContract).filter(ProjectContract.project_id == project_id).first()
    if not row:
        # Create from sources first
        get_contract(db, project_id)
        row = db.query(ProjectContract).filter(ProjectContract.project_id == project_id).first()
    if not row:
        return None
    if expected_version is not None and row.version != expected_version:
        logger.warning("Contract patch rejected: version mismatch project=%s expected=%s current=%s", project_id, expected_version, row.version)
        return None
    current = copy.deepcopy(row.contract_json)
    merged = _deep_merge(current, patch_json)
    now = datetime.utcnow()
    updated_at_str = now.isoformat() + "Z"
    merged["meta"] = merged.get("meta", {})
    merged["meta"]["updated_at"] = updated_at_str
    merged["meta"]["last_updated_by"] = source
    merged["meta"]["audit"] = list(merged["meta"].get("audit", [])) + [
        {"at": updated_at_str, "event": "contract_patched", "by": source, "changed_keys": list(patch_json.keys())},
    ]
    row.contract_json = merged
    row.version = (row.version or 1) + 1
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row.contract_json
