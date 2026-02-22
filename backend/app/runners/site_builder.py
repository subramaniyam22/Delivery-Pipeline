import json
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from app.utils.signed_tokens import generate_signed_token
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Artifact, Stage, TemplateRegistry
from app.services import artifact_service

logger = logging.getLogger(__name__)


def clone_template(template: TemplateRegistry, workdir: str) -> str:
    """
    Get template source into workdir/template. Uses build_source_type/build_source_ref when set
    (versioned clone); otherwise falls back to repo_url + default_branch.
    - git + build_source_ref: clone that branch/tag (immutable ref).
    - s3 + build_source_ref: download zip from S3 key and expand.
    """
    repo_dir = os.path.join(workdir, "template")
    source_type = getattr(template, "build_source_type", None)
    source_ref = getattr(template, "build_source_ref", None)

    if source_type in ("s3", "s3_zip") and source_ref:
        # Versioned artifact: download zip from S3 and expand
        try:
            from app.services.storage import get_s3_assets_backend
            backend = get_s3_assets_backend()
            if not backend:
                raise RuntimeError("S3 not configured; cannot download template zip")
            os.makedirs(repo_dir, exist_ok=True)
            zip_path = os.path.join(workdir, "template.zip")
            data = backend.read_bytes(source_ref)
            with open(zip_path, "wb") as f:
                f.write(data)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(repo_dir)
            os.remove(zip_path)
            return repo_dir
        except Exception as e:
            raise RuntimeError(f"Template S3 source failed ({source_ref}): {e}") from e

    if source_type == "git" and source_ref:
        # Versioned git ref (branch or tag)
        branch_or_tag = source_ref
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch_or_tag, template.repo_url, repo_dir],
            check=True,
        )
        return repo_dir

    # Fallback: repo_url + default_branch
    branch = (template.default_branch or "main").strip()
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, template.repo_url, repo_dir],
        check=True,
    )
    return repo_dir


def _load_artifact_bytes(artifact: Artifact) -> bytes:
    if artifact.url and (artifact.url.startswith("http://") or artifact.url.startswith("https://")):
        resp = requests.get(artifact.url, timeout=20)
        resp.raise_for_status()
        return resp.content
    return artifact_service.get_artifact_bytes(artifact)


def apply_assets(mapping_plan_json: Optional[List[Dict[str, Any]]], assets: List[Artifact], local_path: str) -> None:
    if not mapping_plan_json:
        return
    assets_by_id = {str(a.id): a for a in assets}
    assets_by_type = {}
    for asset in assets:
        assets_by_type.setdefault(asset.artifact_type or asset.type, []).append(asset)

    for item in mapping_plan_json:
        dest_path = item.get("dest_path")
        if not dest_path:
            continue
        artifact_id = item.get("artifact_id")
        artifact_type = item.get("artifact_type")
        artifact = None
        if artifact_id and artifact_id in assets_by_id:
            artifact = assets_by_id[artifact_id]
        elif artifact_type and artifact_type in assets_by_type:
            artifact = assets_by_type[artifact_type][0]
        if not artifact:
            continue
        content = _load_artifact_bytes(artifact)
        final_path = os.path.join(local_path, dest_path.lstrip("/"))
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        with open(final_path, "wb") as handle:
            handle.write(content)


def _run_command(cmd: List[str], cwd: str) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def build_site(local_path: str) -> Tuple[str, str]:
    if os.path.exists(os.path.join(local_path, "package.json")):
        _run_command(["npm", "install"], cwd=local_path)
        _run_command(["npm", "run", "build"], cwd=local_path)
        for candidate in ["dist", "out", "build"]:
            out_dir = os.path.join(local_path, candidate)
            if os.path.isdir(out_dir):
                return out_dir, candidate
        raise RuntimeError("Build completed but no output directory found")

    if os.path.exists(os.path.join(local_path, "build.sh")):
        _run_command(["bash", "build.sh"], cwd=local_path)
        out_dir = os.path.join(local_path, "dist")
        if os.path.isdir(out_dir):
            return out_dir, "dist"
        raise RuntimeError("build.sh did not create dist/")

    if os.path.exists(os.path.join(local_path, "index.html")):
        return local_path, "static"

    raise RuntimeError("No build strategy found for template")


def package_build(dist_path: str, workdir: str) -> str:
    zip_base = os.path.join(workdir, "build_output")
    archive_path = shutil.make_archive(zip_base, "zip", dist_path)
    return archive_path


def create_preview(dist_path: str, project_id, ttl_hours: int) -> Tuple[str, str]:
    token = generate_signed_token(
        {"project_id": str(project_id), "purpose": "preview"},
        int(ttl_hours * 3600),
    )
    base_url = settings.BACKEND_URL or "http://localhost:8000"
    preview_url = f"{base_url.rstrip('/')}/public/preview/{token}"
    return token, preview_url


def _inject_client_contract(repo_dir: str, contract: Dict[str, Any]) -> None:
    """Write normalized contract to data/client_contract.json for template consumption."""
    data_dir = os.path.join(repo_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "client_contract.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2)


def build_and_package(
    db: Session,
    project_id,
    stage: Stage,
    template: TemplateRegistry,
    assets: List[Artifact],
    mapping_plan_json: Optional[List[Dict[str, Any]]],
    preview_strategy: str,
    actor_user_id,
    run_id: Optional[UUID] = None,
    contract: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from app.services.storage import (
        build_preview_prefix,
        get_preview_public_url,
        get_preview_url,
        get_s3_assets_backend,
        upload_preview_site,
        copy_preview_to_delivery_current,
    )

    with tempfile.TemporaryDirectory() as workdir:
        repo_dir = clone_template(template, workdir)
        if contract:
            _inject_client_contract(repo_dir, contract)
        baseline_dir = None
        baseline_src = os.path.join(repo_dir, "baseline")
        if os.path.isdir(baseline_src):
            baseline_dir = os.path.join(settings.UPLOAD_DIR, "baselines", str(project_id))
            if os.path.exists(baseline_dir):
                shutil.rmtree(baseline_dir)
            os.makedirs(os.path.dirname(baseline_dir), exist_ok=True)
            shutil.copytree(baseline_src, baseline_dir)
        apply_assets(mapping_plan_json, assets, repo_dir)
        dist_path, output_kind = build_site(repo_dir)
        index_path = os.path.join(dist_path, "index.html")
        if not os.path.isfile(index_path):
            raise RuntimeError("Build must output index.html; missing in output directory")
        zip_path = package_build(dist_path, workdir)

        with open(zip_path, "rb") as handle:
            zip_bytes = handle.read()
        artifact_service.create_artifact_from_bytes(
            db=db,
            project_id=project_id,
            stage=stage,
            filename=f"build-{project_id}.zip",
            content=zip_bytes,
            artifact_type="build_zip",
            uploaded_by_user_id=actor_user_id,
            metadata_json={"output_kind": output_kind},
        )

        preview_token = None
        preview_url = None
        use_s3_preview = (
            run_id
            and getattr(template, "build_source_type", None) in ("s3", "s3_zip")
            and getattr(template, "build_source_ref", None)
            and get_s3_assets_backend() is not None
        )
        if use_s3_preview:
            upload_preview_site(str(project_id), str(run_id), dist_path)
            preview_url = get_preview_public_url(str(project_id), str(run_id), "")
            logger.info(
                "build_upload preview_prefix=%s cloudfront_url=%s",
                build_preview_prefix(str(project_id), str(run_id)),
                get_preview_url(str(project_id), str(run_id), ""),
                extra={"project_id": str(project_id), "run_id": str(run_id), "preview_url": preview_url},
            )
        elif preview_strategy == "serve_static_preview":
            preview_token, public_preview_url = create_preview(dist_path, project_id, settings.PREVIEW_TOKEN_TTL_HOURS)
            preview_url = f"file://{os.path.join(dist_path, 'index.html')}"
            preview_zip_path = package_build(dist_path, workdir)
            with open(preview_zip_path, "rb") as handle:
                preview_bytes = handle.read()
            artifact_service.create_artifact_from_bytes(
                db=db,
                project_id=project_id,
                stage=stage,
                filename=f"preview-{project_id}.zip",
                content=preview_bytes,
                artifact_type="preview_package",
                uploaded_by_user_id=actor_user_id,
                metadata_json={"token": preview_token, "preview_url": public_preview_url},
            )
        else:
            preview_url = f"file://{os.path.join(dist_path, 'index.html')}"

        template_info = f"{template.repo_url or ''}@{template.default_branch or 'main'}"
        if getattr(template, "build_source_type", None) in ("s3", "s3_zip"):
            template_info = getattr(template, "build_source_ref", "") or template_info
        else:
            try:
                commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir).decode().strip()
                template_info = f"{template_info}#{commit}"
            except Exception:
                pass

        artifact_service.create_artifact_from_bytes(
            db=db,
            project_id=project_id,
            stage=stage,
            filename=f"template-source-{project_id}.txt",
            content=template_info.encode("utf-8"),
            artifact_type="template_source_ref",
            uploaded_by_user_id=actor_user_id,
            metadata_json={"repo_url": getattr(template, "repo_url", None), "branch": template.default_branch},
        )

    return {
        "preview_url": preview_url,
        "preview_token": preview_token,
        "baseline_dir": baseline_dir,
        "used_s3_preview": use_s3_preview,
        "run_id": run_id,
    }
