from dataclasses import dataclass, field
from typing import Any

from packages.security.sanitization import sanitize_for_storage


@dataclass(frozen=True)
class SourceAuthConfig:
    source_id: str
    auth_mode: str
    secret_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def safe_metadata(self) -> dict[str, Any]:
        return sanitize_for_storage(self.metadata)
