import re


_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def estimate_tokens(text: str) -> int:
    """Cheap tokenizer estimate for budgeting before model-specific tokenizers exist."""

    if not text:
        return 0
    return len(_TOKEN_PATTERN.findall(text))
