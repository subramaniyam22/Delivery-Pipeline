from typing import Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


def s3_enabled() -> bool:
    return bool(settings.S3_BUCKET and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def build_public_url(key: str) -> str:
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    region = settings.AWS_REGION or "us-east-1"
    return f"https://{settings.S3_BUCKET}.s3.{region}.amazonaws.com/{key}"


def upload_bytes_to_s3(data: bytes, key: str, content_type: Optional[str] = None) -> str:
    """Upload bytes to S3 and return public URL."""
    client = get_s3_client()
    extra_args = {"ACL": "public-read"}
    if content_type:
        extra_args["ContentType"] = content_type
    try:
        client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data, **extra_args)
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 upload failed: {exc}") from exc
    return build_public_url(key)
