from dataclasses import dataclass


@dataclass(frozen=True)
class RerankedCandidate:
    chunk_id: str
    score: float


class RerankerClient:
    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        _ = query
        return sorted(candidates, key=lambda item: item.get("score", 0), reverse=True)
