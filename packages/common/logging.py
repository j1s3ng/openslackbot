import logging
from typing import Any

from packages.security.sanitization import sanitize_metadata


class SanitizingFormatter(logging.Formatter):
    """Formatter that sanitizes structured args before rendering log messages."""

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.args, dict):
            record.args = sanitize_metadata(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(sanitize_metadata(arg) for arg in record.args)
        return super().format(record)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        SanitizingFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def safe_log_value(value: Any) -> Any:
    return sanitize_metadata(value)
