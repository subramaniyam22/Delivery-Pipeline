import os
import shutil
import subprocess
import tempfile
import zipfile
from app.utils.signed_tokens import generate_signed_token
from typing import Any, Dict, List, Optional, Tuple

import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Artifact, Stage, TemplateRegistry
from app.services import artifact_service


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

    if source_type == "s3" and source_ref:
        # Versioned artifact: download zip from S3 and expand
        try:
            from app.services.storage import get_storage_backend
            storage = get_storage_backend()
            os.makedirs(repo_dir, exist_ok=True)
            zip_path = os.path.join(workdir, "template.zip")
            if hasattr(storage, "download_file") and callable(getattr(storage, "download_file")):
                storage.download_file(source_ref, zip_path)
            else:
                # S3Service style: download_file(object_name, file_path)
                from app.services.s3_service import S3Service
                s3 = S3Service()
                if not s3.download_file(source_ref, zip_path):
                    raise RuntimeError(f"Failed to download template from S3: {source_ref}")
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


def build_and_package(
    db: Session,
    project_id,
    stage: Stage,
    template: TemplateRegistry,
    assets: List[Artifact],
    mapping_plan_json: Optional[List[Dict[str, Any]]],
    preview_strategy: str,
    actor_user_id,
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as workdir:
        repo_dir = clone_template(template, workdir)
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
        if preview_strategy == "serve_static_preview":
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

        template_info = f"{template.repo_url}@{template.default_branch}"
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
            metadata_json={"repo_url": template.repo_url, "branch": template.default_branch},
        )

    return {
        "preview_url": preview_url,
        "preview_token": preview_token,
        "baseline_dir": baseline_dir,
    }
