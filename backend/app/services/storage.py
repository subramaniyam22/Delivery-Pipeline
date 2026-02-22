import hashlib
import json
import os
import mimetypes
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

# S3 key prefixes (bucket: delivery-pipeline-assets-prod or configured)
TEMPLATES_PREFIX = "templates/"
PREVIEWS_PREFIX = "previews/"
DELIVERIES_PREFIX = "deliveries/"
ARTIFACTS_PREFIX = "artifacts/"


@dataclass
class StoredObject:
    storage_key: str
    url: Optional[str]
    content_type: str
    size_bytes: int
    checksum: str


class StorageBackend:
    def save_bytes(self, path: str, data: bytes, content_type: Optional[str] = None) -> StoredObject:
        raise NotImplementedError

    def save_file(self, path: str, local_file_path: str, content_type: Optional[str] = None) -> StoredObject:
        raise NotImplementedError

    def get_url(self, path: str, expires_seconds: int = 3600) -> Optional[str]:
        raise NotImplementedError

    def delete(self, path: str) -> None:
        raise NotImplementedError

    def read_bytes(self, path: str) -> bytes:
        raise NotImplementedError


def _guess_content_type(path: str, fallback: str = "application/octet-stream") -> str:
    return mimetypes.guess_type(path)[0] or fallback


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class LocalDiskStorage(StorageBackend):
    def __init__(self, base_dir: Optional[str] = None, public_base_url: Optional[str] = None) -> None:
        self.base_dir = base_dir or settings.UPLOAD_DIR
        self.public_base_url = public_base_url or settings.STORAGE_PUBLIC_BASE_URL

    def _full_path(self, path: str) -> str:
        cleaned = path.lstrip("/").replace("\\", "/")
        return os.path.join(self.base_dir, cleaned)

    def save_bytes(self, path: str, data: bytes, content_type: Optional[str] = None) -> StoredObject:
        full_path = self._full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as handle:
            handle.write(data)
        resolved_content_type = content_type or _guess_content_type(path)
        return StoredObject(
            storage_key=path,
            url=self.get_url(path),
            content_type=resolved_content_type,
            size_bytes=len(data),
            checksum=_hash_bytes(data),
        )

    def save_file(self, path: str, local_file_path: str, content_type: Optional[str] = None) -> StoredObject:
        with open(local_file_path, "rb") as handle:
            data = handle.read()
        return self.save_bytes(path, data, content_type=content_type)

    def get_url(self, path: str, expires_seconds: int = 3600) -> Optional[str]:
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{path.lstrip('/')}"
        return self._full_path(path)

    def delete(self, path: str) -> None:
        full_path = self._full_path(path)
        if os.path.exists(full_path):
            os.remove(full_path)

    def read_bytes(self, path: str) -> bytes:
        full_path = self._full_path(path)
        with open(full_path, "rb") as handle:
            return handle.read()


class S3CompatibleStorage(StorageBackend):
    def __init__(
        self,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        public_base_url: Optional[str] = None,
    ) -> None:
        self.bucket = bucket
        self.public_base_url = public_base_url
        self.client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            endpoint_url=endpoint_url or None,
        )

    def save_bytes(self, path: str, data: bytes, content_type: Optional[str] = None) -> StoredObject:
        resolved_content_type = content_type or _guess_content_type(path)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=data,
                ContentType=resolved_content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"S3 upload failed: {exc}") from exc
        return StoredObject(
            storage_key=path,
            url=self.get_url(path),
            content_type=resolved_content_type,
            size_bytes=len(data),
            checksum=_hash_bytes(data),
        )

    def save_file(self, path: str, local_file_path: str, content_type: Optional[str] = None) -> StoredObject:
        resolved_content_type = content_type or _guess_content_type(local_file_path)
        try:
            with open(local_file_path, "rb") as handle:
                data = handle.read()
            return self.save_bytes(path, data, content_type=resolved_content_type)
        except Exception as exc:
            raise RuntimeError(f"S3 upload failed: {exc}") from exc

    def get_url(self, path: str, expires_seconds: int = 3600) -> Optional[str]:
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{path}"
        try:
            return self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": path},
                ExpiresIn=expires_seconds,
            )
        except (BotoCoreError, ClientError):
            return None

    def delete(self, path: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"S3 delete failed: {exc}") from exc

    def read_bytes(self, path: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=path)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"S3 download failed: {exc}") from exc

    def list_keys(self, prefix: str, max_keys: int = 10000) -> List[str]:
        """List object keys under prefix."""
        keys: List[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix, MaxKeys=max_keys):
            for obj in page.get("Contents") or []:
                keys.append(obj["Key"])
        return keys

    def copy_prefix_to_prefix(self, source_prefix: str, dest_prefix: str) -> int:
        """Copy all objects under source_prefix to dest_prefix (same key suffix). Returns count copied."""
        keys = self.list_keys(source_prefix)
        for key in keys:
            if not key.startswith(source_prefix):
                continue
            suffix = key[len(source_prefix) :]
            dest_key = (dest_prefix.rstrip("/") + "/" + suffix).lstrip("/")
            self.client.copy_object(
                CopySource={"Bucket": self.bucket, "Key": key},
                Bucket=self.bucket,
                Key=dest_key,
            )
        return len(keys)

    def upload_directory(self, local_dir: str, s3_prefix: str) -> int:
        """Upload a local directory tree to S3 under s3_prefix. Returns number of files uploaded."""
        if not os.path.isdir(local_dir):
            raise RuntimeError(f"Not a directory: {local_dir}")
        count = 0
        for root, _dirs, files in os.walk(local_dir):
            for name in files:
                path = os.path.join(root, name)
                rel = os.path.relpath(path, local_dir).replace("\\", "/")
                key = f"{s3_prefix.rstrip('/')}/{rel}"
                with open(path, "rb") as f:
                    data = f.read()
                self.save_bytes(key, data, content_type=_guess_content_type(path))
                count += 1
        return count


def _resolve_s3_config() -> Optional[Tuple[str, str, str, Optional[str], Optional[str], Optional[str]]]:
    bucket = settings.S3_BUCKET or settings.AWS_S3_BUCKET
    access_key = settings.S3_ACCESS_KEY or settings.AWS_ACCESS_KEY_ID
    secret_key = settings.S3_SECRET_KEY or settings.AWS_SECRET_ACCESS_KEY
    region = settings.S3_REGION or settings.AWS_REGION
    endpoint = settings.S3_ENDPOINT_URL
    public_base = settings.S3_PUBLIC_BASE_URL or settings.STORAGE_PUBLIC_BASE_URL
    if not bucket or not access_key or not secret_key:
        return None
    return bucket, access_key, secret_key, region, endpoint, public_base


def get_storage_backend() -> StorageBackend:
    backend = (settings.STORAGE_BACKEND or "local").lower()
    s3_config = _resolve_s3_config()
    if backend == "s3" and s3_config:
        bucket, access_key, secret_key, region, endpoint, public_base = s3_config
        return S3CompatibleStorage(
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            endpoint_url=endpoint,
            public_base_url=public_base,
        )
    if s3_config and backend != "local":
        bucket, access_key, secret_key, region, endpoint, public_base = s3_config
        return S3CompatibleStorage(
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            endpoint_url=endpoint,
            public_base_url=public_base,
        )
    return LocalDiskStorage()


def get_s3_assets_backend() -> Optional[S3CompatibleStorage]:
    """S3 backend for templates/previews/deliveries/artifacts. Returns None if S3 not configured."""
    s3_config = _resolve_s3_config()
    if not s3_config:
        return None
    bucket, access_key, secret_key, region, endpoint, public_base = s3_config
    return S3CompatibleStorage(
        bucket=bucket,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        endpoint_url=endpoint,
        public_base_url=public_base,
    )


# --- Preview bundle helpers (retry + prefix) ---
import time
from typing import Dict, Union

PREVIEW_BUNDLE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
UPLOAD_RETRIES = 3
UPLOAD_RETRY_BACKOFF = 1.0

# AWS S3 pre-signed URL max expiry is 7 days (604800 seconds). Using 1 year causes AuthorizationQueryParametersError.
S3_PRESIGN_MAX_EXPIRY_SECONDS = 604800


def refresh_presigned_thumbnail_url(stored_url: Optional[str]) -> Optional[str]:
    """
    If stored_url is an S3 pre-signed URL (e.g. with X-Amz-Expires=31536000), return a new
    pre-signed URL with S3_PRESIGN_MAX_EXPIRY_SECONDS so S3 does not return 400.
    Otherwise return stored_url unchanged.
    """
    if not stored_url or "X-Amz-" not in stored_url:
        return stored_url
    from urllib.parse import urlparse
    parsed = urlparse(stored_url)
    key = (parsed.path or "").lstrip("/")
    if not key:
        return stored_url
    try:
        backend = get_preview_storage_backend()
        new_url = backend.get_url(key, expires_seconds=S3_PRESIGN_MAX_EXPIRY_SECONDS)
        return new_url or stored_url
    except Exception:
        return stored_url


def _previews_base_dir() -> str:
    """Directory for local preview files (served at /previews)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "generated_previews")


def get_preview_storage_backend() -> StorageBackend:
    """Storage backend for template preview bundles; local writes to generated_previews for /previews mount."""
    backend = (settings.STORAGE_BACKEND or "local").lower()
    s3_config = _resolve_s3_config()
    if backend == "s3" and s3_config:
        bucket, access_key, secret_key, region, endpoint, public_base = s3_config
        return S3CompatibleStorage(
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            endpoint_url=endpoint,
            public_base_url=public_base,
        )
    if s3_config and backend != "local":
        bucket, access_key, secret_key, region, endpoint, public_base = s3_config
        return S3CompatibleStorage(
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            endpoint_url=endpoint,
            public_base_url=public_base,
        )
    base_url = (settings.BACKEND_URL or "http://localhost:8000").rstrip("/") + "/previews"
    return LocalDiskStorage(base_dir=_previews_base_dir(), public_base_url=base_url)


def _retry_upload(fn, *args, **kwargs):
    last_err = None
    for attempt in range(UPLOAD_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            if attempt < UPLOAD_RETRIES - 1:
                time.sleep(UPLOAD_RETRY_BACKOFF * (attempt + 1))
    raise last_err


def upload_preview_bundle(prefix: str, files: Dict[str, Union[str, bytes]]) -> str:
    """
    Upload a set of files under prefix (e.g. templates/residential-modern/v1).
    Returns the preview entry URL (URL to index.html). When using S3 without
    public_base_url, returns a pre-signed URL so the bucket can stay private.
    """
    backend = get_preview_storage_backend()
    total = 0
    for k, v in files.items():
        data = v.encode("utf-8") if isinstance(v, str) else v
        total += len(data)
        if total > PREVIEW_BUNDLE_MAX_BYTES:
            raise RuntimeError(f"Preview bundle exceeds {PREVIEW_BUNDLE_MAX_BYTES} bytes")
    index_key = f"{prefix.rstrip('/')}/index.html" if prefix else "index.html"
    for rel_path, content in files.items():
        data = content.encode("utf-8") if isinstance(content, str) else content
        key = f"{prefix.rstrip('/')}/{rel_path}" if prefix else rel_path

        def _put():
            backend.save_bytes(key, data, content_type=None)
            return backend.get_url(key, expires_seconds=S3_PRESIGN_MAX_EXPIRY_SECONDS)

        _retry_upload(_put)
    # Return the URL for index.html: pre-signed if no public base (private bucket), else public path
    if getattr(backend, "public_base_url", None):
        return f"{backend.public_base_url.rstrip('/')}/{index_key}"
    entry_url = backend.get_url(index_key, expires_seconds=S3_PRESIGN_MAX_EXPIRY_SECONDS)
    if entry_url:
        return entry_url
    base = getattr(backend, "public_base_url", None) or ""
    if prefix:
        base = f"{base.rstrip('/')}/{prefix.rstrip('/')}"
    return f"{base.rstrip('/')}/index.html"


def upload_thumbnail(prefix: str, image_bytes: bytes) -> str:
    """Upload thumbnail image; returns public URL."""
    key = f"{prefix.rstrip('/')}/thumbnail.png" if prefix else "thumbnail.png"

    def _put():
        backend = get_preview_storage_backend()
        backend.save_bytes(key, image_bytes, content_type="image/png")
        return backend.get_url(key, expires_seconds=S3_PRESIGN_MAX_EXPIRY_SECONDS)

    url = _retry_upload(_put)
    if not url:
        raise RuntimeError("Thumbnail upload did not return URL")
    return url


def delete_preview_bundle(prefix: str) -> None:
    """Optionally delete all objects under prefix (best-effort)."""
    backend = get_preview_storage_backend()
    if hasattr(backend, "client") and hasattr(backend, "bucket"):
        try:
            paginator = backend.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=backend.bucket, Prefix=prefix):
                for obj in page.get("Contents") or []:
                    backend.delete(obj["Key"])
        except Exception:
            pass
    # Local: delete directory under base_dir
    if hasattr(backend, "base_dir") and hasattr(backend, "_full_path"):
        import shutil
        full = backend._full_path(prefix)
        if os.path.isdir(full):
            try:
                shutil.rmtree(full)
            except Exception:
                pass


# --- Template ZIP (templates/{template_id}/{version}/template.zip) ---

def template_zip_s3_key(template_id: str, version: str) -> str:
    return f"{TEMPLATES_PREFIX}{template_id}/{version}/template.zip"


def upload_template_zip(template_id: str, version: str, file_bytes: bytes) -> str:
    """Upload template.zip to S3; immutable. Returns S3 key."""
    key = template_zip_s3_key(template_id, version)
    backend = get_s3_assets_backend()
    if not backend:
        raise RuntimeError("S3 not configured; cannot upload template zip")
    backend.save_bytes(key, file_bytes, content_type="application/zip")
    return key


def download_template_zip(template_id: str, version: str) -> bytes:
    """Download template.zip from S3. Raises if not found or S3 not configured."""
    key = template_zip_s3_key(template_id, version)
    backend = get_s3_assets_backend()
    if not backend:
        raise RuntimeError("S3 not configured; cannot download template zip")
    return backend.read_bytes(key)


# --- Previews (previews/{project_id}/{run_id}/site/...) ---

def preview_site_prefix(project_id: str, run_id: str) -> str:
    return f"{PREVIEWS_PREFIX}{project_id}/{run_id}/site/"


def get_preview_public_url(project_id: str, run_id: str, path: str = "") -> str:
    """Public URL for preview (CloudFront). path e.g. '' or 'index.html'."""
    base = (settings.PREVIEW_PUBLIC_BASE_URL or "").rstrip("/")
    segs = [base, "previews", project_id, run_id, "site"]
    if path:
        segs.append(path.lstrip("/"))
    return "/".join(segs)


def upload_preview_site(project_id: str, run_id: str, local_dir: str) -> None:
    """Upload local directory to S3 previews/{project_id}/{run_id}/site/."""
    backend = get_s3_assets_backend()
    if not backend:
        raise RuntimeError("S3 not configured; cannot upload preview site")
    prefix = preview_site_prefix(project_id, run_id)
    backend.upload_directory(local_dir, prefix)


# --- Deliveries (deliveries/{project_id}/current/site/...) ---

def delivery_current_prefix(project_id: str) -> str:
    return f"{DELIVERIES_PREFIX}{project_id}/current/site/"


def delivery_run_prefix(project_id: str, run_id: str) -> str:
    return f"{DELIVERIES_PREFIX}{project_id}/{run_id}/site/"


def get_delivery_public_url(project_id: str, path: str = "") -> str:
    """Public URL for stable delivery (CloudFront)."""
    base = (settings.DELIVERY_PUBLIC_BASE_URL or "").rstrip("/")
    segs = [base, "deliveries", project_id, "current", "site"]
    if path:
        segs.append(path.lstrip("/"))
    return "/".join(segs)


def copy_preview_to_delivery_current(project_id: str, run_id: str) -> int:
    """Copy S3 preview site to deliveries/{project_id}/current/site/. Returns object count."""
    backend = get_s3_assets_backend()
    if not backend:
        raise RuntimeError("S3 not configured; cannot copy to delivery")
    src = preview_site_prefix(project_id, run_id)
    dest = delivery_current_prefix(project_id)
    return backend.copy_prefix_to_prefix(src, dest)


def copy_preview_to_delivery_run(project_id: str, run_id: str) -> int:
    """Copy preview to deliveries/{project_id}/{run_id}/site/ (history)."""
    backend = get_s3_assets_backend()
    if not backend:
        raise RuntimeError("S3 not configured")
    src = preview_site_prefix(project_id, run_id)
    dest = delivery_run_prefix(project_id, run_id)
    return backend.copy_prefix_to_prefix(src, dest)


# --- Proof packs (artifacts/{project_id}/{stage_key}/{run_id}/...) ---

PROOF_PACK_SOFT_MB = 50
PROOF_PACK_HARD_MB = 200


def artifacts_prefix(project_id: str, stage_key: str, run_id: str) -> str:
    return f"{ARTIFACTS_PREFIX}{project_id}/{stage_key}/{run_id}/"


def upload_proof_pack(
    project_id: str,
    stage_key: str,
    run_id: str,
    files: Dict[str, Union[bytes, str]],
    manifest: Dict[str, Any],
    soft_mb: int = PROOF_PACK_SOFT_MB,
    hard_mb: int = PROOF_PACK_HARD_MB,
) -> Dict[str, Any]:
    """
    Upload proof pack files + manifest to artifacts/{project_id}/{stage_key}/{run_id}/.
    manifest must include project_id, run_id, stage_key, timestamps, preview_url, etc.
    Returns dict: manifest_s3_key, total_bytes, exceeded_soft (bool), exceeded_hard (bool).
    If exceeded_hard, caller should mark stage failed and stop retries.
    """
    backend = get_s3_assets_backend()
    if not backend:
        raise RuntimeError("S3 not configured; cannot upload proof pack")
    prefix = artifacts_prefix(project_id, stage_key, run_id)
    total = 0
    for name, content in files.items():
        data = content.encode("utf-8") if isinstance(content, str) else content
        key = f"{prefix}{name}"
        backend.save_bytes(key, data)
        total += len(data)
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    manifest_key = f"{prefix}manifest.json"
    backend.save_bytes(manifest_key, manifest_bytes, content_type="application/json")
    total += len(manifest_bytes)
    total_mb = total / (1024 * 1024)
    return {
        "manifest_s3_key": manifest_key,
        "total_bytes": total,
        "exceeded_soft": total_mb > soft_mb,
        "exceeded_hard": total_mb > hard_mb,
    }
