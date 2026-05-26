from typing import Any

from qdrant_client import QdrantClient

from packages.common.config import get_settings
from packages.security.sanitization import sanitize_for_storage


class QdrantStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.collection = settings.qdrant_collection
        self.client = QdrantClient(url=settings.qdrant_url)

    @staticmethod
    def safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return sanitize_for_storage(payload)
