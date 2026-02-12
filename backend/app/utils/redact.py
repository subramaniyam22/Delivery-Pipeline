"""Redact secrets from text before storing (e.g. raw LLM output)."""
import re

# Patterns that may indicate secrets (redact with placeholder)
SK_PATTERN = re.compile(r"sk-[a-zA-Z0-9-_]{20,}", re.IGNORECASE)
# Generic env-like key=value where value looks like a key
ENV_SECRET_PATTERN = re.compile(
    r"(\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*[\"']?)([a-zA-Z0-9-_]{20,})([\"']?)",
    re.IGNORECASE,
)


def redact_secrets(text: str | None) -> str:
    if not text:
        return ""
    out = SK_PATTERN.sub("sk-***REDACTED***", text)
    out = ENV_SECRET_PATTERN.sub(r"\g<1>***REDACTED***\g<3>", out)
    return out
