from app.config import settings
from app.services.storage import get_storage_backend, LocalDiskStorage, S3CompatibleStorage


def test_storage_backend_local_default():
    original_backend = settings.STORAGE_BACKEND
    original_bucket = settings.S3_BUCKET
    original_access = settings.S3_ACCESS_KEY
    original_secret = settings.S3_SECRET_KEY
    try:
        settings.STORAGE_BACKEND = "local"
        settings.S3_BUCKET = None
        settings.S3_ACCESS_KEY = None
        settings.S3_SECRET_KEY = None
        backend = get_storage_backend()
        assert isinstance(backend, LocalDiskStorage)
    finally:
        settings.STORAGE_BACKEND = original_backend
        settings.S3_BUCKET = original_bucket
        settings.S3_ACCESS_KEY = original_access
        settings.S3_SECRET_KEY = original_secret


def test_storage_backend_s3_selection():
    original_backend = settings.STORAGE_BACKEND
    original_bucket = settings.S3_BUCKET
    original_access = settings.S3_ACCESS_KEY
    original_secret = settings.S3_SECRET_KEY
    try:
        settings.STORAGE_BACKEND = "s3"
        settings.S3_BUCKET = "bucket"
        settings.S3_ACCESS_KEY = "access"
        settings.S3_SECRET_KEY = "secret"
        backend = get_storage_backend()
        assert isinstance(backend, S3CompatibleStorage)
    finally:
        settings.STORAGE_BACKEND = original_backend
        settings.S3_BUCKET = original_bucket
        settings.S3_ACCESS_KEY = original_access
        settings.S3_SECRET_KEY = original_secret
