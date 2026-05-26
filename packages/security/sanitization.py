from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REDACTED = "[REDACTED]"

SENSITIVE_KEY_NAMES = {
    "authorization",
    "cookie",
    "set_cookie",
    "x_api_key",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "client_secret",
    "password",
    "token",
    "session",
    "csrf",
}

SENSITIVE_QUERY_PARAMS = {
    "token",
    "api_key",
    "access_token",
    "key",
    "secret",
    "session",
    "auth",
}


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    return (
        normalized in SENSITIVE_KEY_NAMES
        or normalized.endswith("_token")
        or normalized.endswith("_password")
        or normalized.endswith("_secret")
        or normalized.endswith("_session")
        or "cookie" in normalized
    )


def sanitize_url(url: str) -> str:
    """Redact sensitive query parameters from a URL-like string."""

    try:
        parts = urlsplit(url)
    except ValueError:
        return url

    if not parts.scheme or not parts.netloc:
        return url

    if not parts.query:
        return url

    safe_params = []
    changed = False
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in SENSITIVE_QUERY_PARAMS:
            safe_params.append((key, REDACTED))
            changed = True
        else:
            safe_params.append((key, value))

    if not changed:
        return url

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(safe_params, doseq=True),
            parts.fragment,
        )
    )


def sanitize_metadata(value: Any) -> Any:
    """Recursively redact credentials from metadata before storage or logging."""

    if isinstance(value, Mapping):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and is_sensitive_key(key):
                sanitized[key] = REDACTED
            else:
                sanitized[key] = sanitize_metadata(item)
        return sanitized

    if isinstance(value, tuple):
        return tuple(sanitize_metadata(item) for item in value)

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [sanitize_metadata(item) for item in value]

    if isinstance(value, str):
        return sanitize_url(value)

    return value


def sanitize_headers(headers: Mapping[str, Any]) -> dict[str, Any]:
    return sanitize_metadata(dict(headers))


def sanitize_for_storage(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    return sanitize_metadata(dict(metadata))
