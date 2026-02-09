from app.config import settings
from app.utils.signed_tokens import generate_signed_token, verify_signed_token


def test_token_rotation_accepts_previous_key():
    original_current = settings.SECRET_KEY_CURRENT
    original_previous = settings.SECRET_KEY_PREVIOUS
    try:
        settings.SECRET_KEY_CURRENT = "old-key"
        settings.SECRET_KEY_PREVIOUS = None
        token = generate_signed_token({"project_id": "proj-123", "purpose": "preview"}, 300)

        settings.SECRET_KEY_CURRENT = "new-key"
        settings.SECRET_KEY_PREVIOUS = "old-key"
        payload = verify_signed_token(token, purpose="preview")
        assert payload is not None
        assert payload["project_id"] == "proj-123"
    finally:
        settings.SECRET_KEY_CURRENT = original_current
        settings.SECRET_KEY_PREVIOUS = original_previous
