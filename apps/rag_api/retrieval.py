from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    text: str
    score: float
    metadata: dict


def normalize_query(query: str) -> str:
    return " ".join(query.split())
