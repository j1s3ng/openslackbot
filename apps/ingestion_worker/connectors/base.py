from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    external_id: str | None
    uri: str
    canonical_uri: str
    title: str | None
    content_type: str | None
    raw_content: bytes | str
    normalized_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceConnector(Protocol):
    def discover(self) -> Iterable[str]:
        raise NotImplementedError

    def should_fetch(self, uri: str, previous_metadata: dict[str, Any] | None) -> bool:
        raise NotImplementedError

    def fetch(self, uri: str) -> RawDocument:
        raise NotImplementedError
