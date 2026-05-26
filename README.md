# local-slack-rag-bot

Local-first Slack RAG assistant for technical work questions. The target stack is Slack Bolt, FastAPI, Postgres, Redis/RQ, Qdrant, LM Studio-hosted GPT-OSS-120B, Qwen3-Embedding-8B, and Qwen3-Reranker-8B.

This repository is being built in small vertical slices. The first slice establishes project metadata, local service configuration, database schema, credential-safe metadata sanitization, and citation validation.

## Local services

```bash
docker compose up -d postgres redis qdrant
```

These services are intended for local/LAN use only. Do not expose Postgres, Redis, Qdrant, or LM Studio to the public internet.

## Python setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pytest
```

## Slack setup

Use Slack Socket Mode for local hosting. No public port forwarding is required because the bot opens an outbound WebSocket connection to Slack.

1. Create a Slack app at <https://api.slack.com/apps>.
2. Enable Socket Mode.
3. Create an app-level token with `connections:write`; store it as `SLACK_APP_TOKEN`.
4. Add bot scopes such as `chat:write`, `app_mentions:read`, and the relevant `message.*` history scopes for the surfaces you want to monitor.
5. Install the app and store the bot token as `SLACK_BOT_TOKEN`.
6. Invite the bot to the target channels.

## Safety rules

- All model calls should go to local or approved internal endpoints.
- Credentials are loaded only at runtime from environment variables or a secret provider.
- Stored metadata, logs, prompts, citations, and vector payloads must not contain tokens, cookies, auth headers, passwords, refresh tokens, or session credentials.
- Slack progress UI should show safe app-generated progress only, never hidden chain-of-thought.

## Current first-slice modules

- `packages/common/config.py` - Pydantic settings loader.
- `packages/db/models.py` - SQLAlchemy models for RAG sources, documents, chunks, Slack conversations, memory, troubleshooting, permissions, feedback, fetches, discovered URLs, and source auth configs.
- `packages/db/migrations/versions/0001_initial.py` - Initial Alembic migration.
- `packages/security/sanitization.py` - Recursive metadata sanitizer and sensitive URL query redaction.
- `apps/rag_api/citation_validator.py` - Source ID citation extraction and validation.
