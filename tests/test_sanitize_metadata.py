from packages.security.sanitization import REDACTED, sanitize_headers, sanitize_metadata, sanitize_url


def test_sensitive_headers_are_redacted_case_insensitively() -> None:
    headers = {
        "Authorization": "Bearer test-token-value",
        "x-api-key": "test-api-key-value",
        "Content-Type": "application/json",
    }

    sanitized = sanitize_headers(headers)

    assert sanitized["Authorization"] == REDACTED
    assert sanitized["x-api-key"] == REDACTED
    assert sanitized["Content-Type"] == "application/json"


def test_nested_sensitive_metadata_is_redacted() -> None:
    metadata = {
        "safe": "keep",
        "auth": {
            "access_token": "access-token-value",
            "refresh_token": "refresh-token-value",
            "client_secret": "client-secret-value",
        },
        "items": [{"password": "password-value"}, {"session": "session-value"}],
        "secret_ref": "env:VENDOR_DOCS_API_TOKEN",
    }

    sanitized = sanitize_metadata(metadata)

    assert sanitized["safe"] == "keep"
    assert sanitized["auth"]["access_token"] == REDACTED
    assert sanitized["auth"]["refresh_token"] == REDACTED
    assert sanitized["auth"]["client_secret"] == REDACTED
    assert sanitized["items"][0]["password"] == REDACTED
    assert sanitized["items"][1]["session"] == REDACTED
    assert sanitized["secret_ref"] == "env:VENDOR_DOCS_API_TOKEN"


def test_sensitive_query_parameters_are_redacted() -> None:
    url = "https://example.com/docs/page?token=abc&topic=sharing&api_key=def&key=ghi#section"

    sanitized = sanitize_url(url)

    assert "token=%5BREDACTED%5D" in sanitized
    assert "api_key=%5BREDACTED%5D" in sanitized
    assert "key=%5BREDACTED%5D" in sanitized
    assert "topic=sharing" in sanitized
    assert sanitized.endswith("#section")


def test_urls_inside_metadata_are_sanitized() -> None:
    metadata = {
        "uri": "https://vendor.example/api?access_token=abc&version=1",
        "canonical_uri": "https://vendor.example/api?version=1",
    }

    sanitized = sanitize_metadata(metadata)

    assert "access_token=%5BREDACTED%5D" in sanitized["uri"]
    assert sanitized["canonical_uri"] == "https://vendor.example/api?version=1"
