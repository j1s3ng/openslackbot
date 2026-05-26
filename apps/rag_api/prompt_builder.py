SYSTEM_PROMPT = """You are a local Slack RAG troubleshooting assistant.
Use only approved retrieved sources.
Ask targeted questions when required information is missing.
Do not invent facts or sources.
Cite factual claims with source IDs like [S1].
Prefer internal docs over external docs when they conflict.
Never reveal hidden chain-of-thought.
Never include secrets, tokens, cookies, or credentials in prompts or answers."""


def build_rag_prompt(
    *,
    rolling_summary: str,
    facts_json: str,
    recent_messages: str,
    source_cards: str,
    user_message: str,
) -> list[dict[str, str]]:
    user_content = f"""CONVERSATION SUMMARY:
{rolling_summary}

STRUCTURED FACTS:
{facts_json}

RECENT THREAD MESSAGES:
{recent_messages}

RETRIEVED SOURCES:
{source_cards}

CURRENT USER MESSAGE:
{user_message}

RESPONSE INSTRUCTIONS:
- If enough information exists, answer with citations.
- If not enough information exists, ask up to two targeted questions.
- Include a short "Why I'm asking" explanation when requesting info.
- End with "Sources used" when sources are cited."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
