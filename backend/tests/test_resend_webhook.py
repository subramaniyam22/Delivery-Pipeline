"""Tests for Resend webhook endpoint POST /api/webhooks/resend."""
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_resend_webhook_503_when_secret_missing():
    """Returns 503 when RESEND_WEBHOOK_SECRET is not configured."""
    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.RESEND_WEBHOOK_SECRET = ""
        mock_settings.CHAT_LOG_WEBHOOK_SECRET = None  # avoid side effects from other routes
        response = client.post(
            "/api/webhooks/resend",
            content=b'{"type":"email.sent"}',
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 503
    assert "RESEND_WEBHOOK_SECRET" in response.json().get("detail", "")


def test_resend_webhook_400_when_svix_headers_missing():
    """Returns 400 when Svix headers (svix-id, svix-timestamp, svix-signature) are missing."""
    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.RESEND_WEBHOOK_SECRET = "whsec_test_secret"
        response = client.post(
            "/api/webhooks/resend",
            content=b'{"type":"email.sent"}',
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 400
    assert "Svix" in response.json().get("detail", "") or "svix" in response.json().get("detail", "").lower()
