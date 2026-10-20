# local-slack-rag-bot Agent Guide

## Project overview

`local-slack-rag-bot` is a local-first Slack RAG assistant for technical work questions. Slack is the user interface, Postgres stores conversations and source metadata, Qdrant stores vector payloads, Redis backs background jobs, and LM Studio hosts the local GPT-OSS-120B generation model.

Retrieval quality, source grounding, and credential safety are more important than minimizing compute. The default local retrieval stack is Qwen3-Embedding-8B for embeddings and Qwen3-Reranker-8B for reranking, with Qwen3-Reranker-4B available as a lower-latency fallback.

## Coding conventions

- Use Python 3.11+.
- Prefer FastAPI, Slack Bolt for Python, SQLAlchemy, Alembic, Pydantic settings, Qdrant, Redis/RQ, and httpx.
- Keep code typed where practical and small enough to test directly.
- Prefer explicit source metadata and stable IDs over inferred state.
- Convert structured JSON into readable embedding text; keep the structured data in Postgres JSONB for audit/filtering.
- Keep chunk text independently understandable and preserve page, section, heading, version, and authority metadata.
- Keep public interfaces conservative and compatible with persisted data.

## Build and test commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
mypy apps packages
docker compose up -d postgres redis qdrant
alembic -c packages/db/alembic.ini upgrade head
```

## Safety constraints

- All AI inference should run locally or on approved internal infrastructure.
- Never send Slack messages, internal documents, source content, credentials, or prompts to external AI APIs.
- Never expose hidden chain-of-thought. Slack progress updates must be app-generated summaries such as "Searching docs" or "Validating citations".
- Do not expose Postgres, Redis, Qdrant, or LM Studio to the public internet.
- Slack Socket Mode is preferred so no public port forwarding is required.

## Credential handling rules

- Connector credentials are only loaded at connector/scraper runtime from environment variables or an approved secret provider.
- Store secret references only, such as `env:VENDOR_DOCS_API_TOKEN`.
- Never store tokens, cookies, API keys, auth headers, usernames, passwords, refresh tokens, session credentials, or scraping secrets in:
  - `rag_sources.config`
  - document/chunk metadata
  - Qdrant payloads
  - source fetch metadata
  - logs
  - prompts
  - citations
- All stored request/response metadata and logs must pass through the sanitizer.

## RAG citation rules

- Source cards must use IDs like `S1`, `S2`, and `S3`.
- The model may cite only source IDs included in the current source cards.
- Factual source-grounded claims require citations.
- Do not invent source IDs, titles, URLs, page ranges, versions, or sections.
- If available sources do not support an answer, say that directly.
- Prefer internal docs over external docs when they conflict.
- Prefer higher-authority and fresher sources when sources conflict.
- End with "Sources used" when citations are used.

## Done criteria

- Docker Compose defines Postgres, Redis, and Qdrant.
- Config loads from `.env` without hardcoded secrets.
- SQLAlchemy models and Alembic migrations exist for the first schema.
- Sanitizer tests prove sensitive keys and URL parameters are redacted.
- Citation validator tests prove invented source IDs are rejected.
- No credentials appear in DB records, vector payload examples, logs, prompts, or test fixtures.
- Focused tests pass before reporting completion.
