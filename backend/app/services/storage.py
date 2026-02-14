import hashlib
import os
import mimetypes
from dataclasses import dataclass
from typing import Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


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
