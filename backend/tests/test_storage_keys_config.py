"""Tests for storage key/URL builders and S3 config validation."""
import pytest
from unittest.mock import patch

from app.config import settings, validate_s3_config_on_startup
from app.services.storage import (
    build_template_key,
    build_preview_prefix,
    build_delivery_prefix,
    build_delivery_history_prefix,
    get_preview_url,
    get_delivery_url,
)


def test_build_template_key():
    key = build_template_key("t1", "v2")
    assert "t1" in key
    assert "v2" in key
    assert key.endswith("template.zip")
    assert "templates" in key or "t1" in key


def test_build_preview_prefix():
    prefix = build_preview_prefix("proj-1", "run-2")
    assert "proj-1" in prefix
    assert "run-2" in prefix
    assert prefix.endswith("site/") or "site" in prefix


def test_build_delivery_prefix():
    prefix = build_delivery_prefix("proj-1")
    assert "proj-1" in prefix
    assert "current" in prefix
    assert "site" in prefix


def test_build_delivery_history_prefix():
    prefix = build_delivery_history_prefix("proj-1", "run-2")
    assert "proj-1" in prefix
    assert "run-2" in prefix
    assert "site" in prefix


def test_get_preview_url():
    url = get_preview_url("proj-1", "run-2", "")
    assert "proj-1" in url
    assert "run-2" in url
    assert "index.html" in url
    assert url.startswith("https://") or url.startswith("http://") or url.startswith("/")


def test_get_preview_url_with_path():
    url = get_preview_url("proj-1", "run-2", "assets/main.js")
    assert "assets/main.js" in url or "main.js" in url


def test_get_delivery_url():
    url = get_delivery_url("proj-1", "")
    assert "proj-1" in url
    assert "index.html" in url
    assert "current" in url
    assert url.startswith("https://") or url.startswith("http://") or url.startswith("/")


def test_get_delivery_url_with_path():
    url = get_delivery_url("proj-1", "page/faq.html")
    assert "page/faq.html" in url or "faq.html" in url


def test_validate_s3_config_fails_when_s3_backend_and_missing_bucket():
    with patch.object(settings, "STORAGE_BACKEND", "s3"):
        with patch.object(settings, "TEMPLATE_S3_BUCKET", ""):
            with patch.object(settings, "S3_BUCKET", None):
                with pytest.raises(ValueError) as exc_info:
                    validate_s3_config_on_startup()
                assert "TEMPLATE_S3_BUCKET" in str(exc_info.value) or "S3_BUCKET" in str(exc_info.value)


def test_validate_s3_config_fails_when_s3_backend_and_missing_credentials():
    with patch.object(settings, "STORAGE_BACKEND", "s3"):
        with patch.object(settings, "TEMPLATE_S3_BUCKET", "my-bucket"):
            with patch.object(settings, "S3_BUCKET", "my-bucket"):
                with patch.object(settings, "S3_ACCESS_KEY", None):
                    with patch.object(settings, "S3_SECRET_KEY", None):
                        with patch.object(settings, "AWS_ACCESS_KEY_ID", None):
                            with patch.object(settings, "AWS_SECRET_ACCESS_KEY", None):
                                with pytest.raises(ValueError) as exc_info:
                                    validate_s3_config_on_startup()
                                assert "S3_ACCESS_KEY" in str(exc_info.value) or "AWS_ACCESS_KEY" in str(exc_info.value)
