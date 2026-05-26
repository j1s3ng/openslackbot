from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceCard:
    source_id: str
    title: str
    source_type: str
    text: str
    section: str | None = None
    pages: str | None = None
    last_updated: str | None = None
    authority_score: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        lines = [
            f"[{self.source_id}]",
            f"title: {self.title}",
            f"source_type: {self.source_type}",
        ]
        if self.section:
            lines.append(f"section: {self.section}")
        if self.pages:
            lines.append(f"pages: {self.pages}")
        if self.last_updated:
            lines.append(f"last_updated: {self.last_updated}")
        if self.authority_score is not None:
            lines.append(f"authority_score: {self.authority_score}")
        lines.extend(["text:", self.text])
        return "\n".join(lines)


def assign_source_cards(chunks: list[dict[str, Any]]) -> list[SourceCard]:
    cards: list[SourceCard] = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata", {})
        cards.append(
            SourceCard(
                source_id=f"S{index}",
                title=metadata.get("document_title") or metadata.get("title") or "Untitled source",
                source_type=metadata.get("source_type") or "unknown",
                section=metadata.get("section_title") or " > ".join(metadata.get("section_path", [])),
                pages=_format_pages(metadata.get("page_start"), metadata.get("page_end")),
                last_updated=metadata.get("last_updated"),
                authority_score=metadata.get("authority_score"),
                text=chunk.get("text", ""),
                metadata=metadata,
            )
        )
    return cards


def _format_pages(page_start: Any, page_end: Any) -> str | None:
    if page_start is None:
        return None
    if page_end is None or page_end == page_start:
        return str(page_start)
    return f"{page_start}-{page_end}"
