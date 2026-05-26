from apps.rag_api.citation_validator import (
    build_guarded_fallback,
    build_strict_retry_instruction,
    extract_citations,
    validate_citations,
)


def test_extract_citations_returns_unique_first_seen_order() -> None:
    assert extract_citations("Use [S2] and [S1], then [S2] again.") == ["[S2]", "[S1]"]


def test_validator_accepts_allowed_source_ids() -> None:
    result = validate_citations(
        "Role hierarchy can grant access to child-role records [S1].",
        {"S1", "S2"},
    )

    assert result.is_valid
    assert result.citations == ["[S1]"]


def test_validator_rejects_invented_source_ids() -> None:
    result = validate_citations(
        "This answer cites a retrieved source [S1] and an invented one [S9].",
        {"S1", "S2"},
    )

    assert not result.is_valid
    assert result.invalid_citations == ["[S9]"]


def test_validator_requires_citations_for_grounded_answer() -> None:
    result = validate_citations(
        "Role hierarchy can affect Salesforce record visibility.",
        {"S1"},
        require_citations=True,
    )

    assert not result.is_valid
    assert result.missing_required_citations


def test_validator_allows_unsupported_fallback_without_citations() -> None:
    result = validate_citations(
        "The available sources do not specify that setting.",
        {"S1"},
        require_citations=True,
    )

    assert result.is_valid


def test_validator_allows_clarifying_question_without_citations() -> None:
    result = validate_citations(
        "Which object is affected: Account, Opportunity, Case, or a custom object?\n\n"
        "Why I'm asking: visibility failures depend on the object and sharing model.",
        {"S1"},
        require_citations=True,
    )

    assert result.is_valid


def test_retry_instruction_lists_allowed_ids() -> None:
    instruction = build_strict_retry_instruction({"S2", "S1"})

    assert "[S1]" in instruction
    assert "[S2]" in instruction
    assert "[S3]" not in instruction


def test_guarded_fallback_lists_source_cards() -> None:
    fallback = build_guarded_fallback(["[S1]\ntitle: Policy\ntext:\n..."])

    assert "available sources do not specify" in fallback.lower()
    assert "[S1]" in fallback
