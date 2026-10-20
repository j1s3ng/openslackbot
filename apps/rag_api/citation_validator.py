from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


CITATION_RE = re.compile(r"\[S\d+\]")


@dataclass(frozen=True)
class CitationValidationResult:
    is_valid: bool
    citations: list[str] = field(default_factory=list)
    invalid_citations: list[str] = field(default_factory=list)
    missing_required_citations: bool = False
    error: str | None = None


def extract_citations(text: str) -> list[str]:
    """Return source citations like `[S1]` in first-seen order without duplicates."""

    seen: set[str] = set()
    citations: list[str] = []
    for match in CITATION_RE.findall(text or ""):
        if match not in seen:
            seen.add(match)
            citations.append(match)
    return citations


def normalize_source_ids(source_ids: Iterable[str]) -> set[str]:
    allowed: set[str] = set()
    for source_id in source_ids:
        value = source_id.strip()
        if not value:
            continue
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]
        allowed.add(value)
    return allowed


def is_unsupported_answer(text: str) -> bool:
    normalized = " ".join((text or "").lower().split())
    unsupported_markers = (
        "available sources do not specify",
        "sources do not specify",
        "retrieved sources do not specify",
        "i do not have enough source",
        "not enough information in the sources",
    )
    return any(marker in normalized for marker in unsupported_markers)


def looks_like_clarifying_question(text: str) -> bool:
    if "?" not in (text or ""):
        return False
    normalized = (text or "").lower()
    return "why i'm asking" in normalized or "why i am asking" in normalized


def validate_citations(
    answer: str,
    allowed_source_ids: Iterable[str],
    *,
    require_citations: bool = True,
    allow_clarifying_question: bool = True,
    allow_unsupported_answer: bool = True,
) -> CitationValidationResult:
    """Validate that answer citations only refer to provided source cards.

    `allowed_source_ids` may contain `S1` or `[S1]`; answer citations must use
    bracketed form such as `[S1]`.
    """

    allowed = normalize_source_ids(allowed_source_ids)
    citations = extract_citations(answer)
    invalid = [citation for citation in citations if citation[1:-1] not in allowed]

    if invalid:
        return CitationValidationResult(
            is_valid=False,
            citations=citations,
            invalid_citations=invalid,
            error=f"Invalid source citations: {', '.join(invalid)}",
        )

    if require_citations and not citations:
        if allow_clarifying_question and looks_like_clarifying_question(answer):
            return CitationValidationResult(is_valid=True, citations=citations)
        if allow_unsupported_answer and is_unsupported_answer(answer):
            return CitationValidationResult(is_valid=True, citations=citations)
        return CitationValidationResult(
            is_valid=False,
            citations=citations,
            missing_required_citations=True,
            error="Source-grounded answers require at least one valid source citation.",
        )

    return CitationValidationResult(is_valid=True, citations=citations)


def build_strict_retry_instruction(allowed_source_ids: Iterable[str]) -> str:
    allowed = ", ".join(f"[{source_id}]" for source_id in sorted(normalize_source_ids(allowed_source_ids)))
    return (
        "Regenerate the answer using only these source IDs: "
        f"{allowed}. Cite factual claims. If the sources do not support the answer, "
        "say the available sources do not specify it."
    )


def build_guarded_fallback(source_cards: Iterable[str]) -> str:
    cards = "\n\n".join(source_cards).strip()
    if not cards:
        return "The available sources do not specify a supported answer."
    return (
        "The available sources do not specify a fully supported answer. "
        "Retrieved source cards are listed below for review.\n\n"
        f"{cards}"
    )
