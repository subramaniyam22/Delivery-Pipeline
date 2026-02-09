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
