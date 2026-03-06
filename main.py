"""OpenSlackBot — single entry point to run everything.

Usage:
    python main.py                  Start the Slack bot
    python main.py ingest FILE...   Ingest files into the knowledge base
    python main.py ingest DIR       Ingest all PDFs/JSONs in a directory
    python main.py status           Show bot & RAG status
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("openslackbot")


def cmd_bot(args):
    """Start the Slack bot."""
    from bot import app, MODEL, TOOL_DEFINITIONS
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    import os

    logger.info("Starting bot — model: %s | %d tools loaded", MODEL, len(TOOL_DEFINITIONS))
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()


def cmd_ingest(args):
    """Ingest PDFs and JSON files into the local knowledge base."""
    from rag import ingest_pdf, ingest_json

    text_fields = [f.strip() for f in args.fields.split(",")] if args.fields else None
    total = 0

    for p in args.paths:
        path = Path(p)
        if not path.exists():
            logger.error("Path not found: %s", p)
            continue

        files = sorted(path.rglob("*")) if path.is_dir() else [path]

        for file in files:
            suffix = file.suffix.lower()
            if suffix == ".pdf":
                n = ingest_pdf(str(file), namespace=args.namespace)
                total += n
                logger.info("  PDF  %s → %d chunks", file.name, n)
            elif suffix == ".json":
                n = ingest_json(str(file), text_fields=text_fields,
                                namespace=args.namespace)
                total += n
                logger.info("  JSON %s → %d records", file.name, n)
            else:
                logger.debug("  Skipping: %s", file.name)

    logger.info("Ingestion complete — %d total documents indexed.", total)


def cmd_status(args):
    """Show current status of the bot configuration and knowledge base."""
    import os

    print("\n=== OpenSlackBot Status ===\n")

    # LM Studio
    base_url = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    model = os.environ.get("LMSTUDIO_MODEL", "gptoss120b")
    print(f"LM Studio:  {base_url}")
    print(f"Model:      {model}")

    # Check LM Studio connectivity
    try:
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key="lm-studio", timeout=5.0)
        models = client.models.list()
        available = [m.id for m in models.data]
        print(f"Available:  {', '.join(available) if available else '(none loaded)'}")
    except Exception as e:
        print(f"Available:  ✗ Cannot connect ({e})")

    # ChromaDB
    chroma_dir = os.environ.get("CHROMA_DIR", "./chroma_data")
    collection_name = os.environ.get("CHROMA_COLLECTION", "openslackbot")
    print(f"\nChromaDB:   {chroma_dir}")
    try:
        import chromadb
        client = chromadb.PersistentClient(path=chroma_dir)
        collection = client.get_or_create_collection(name=collection_name)
        count = collection.count()
        print(f"Collection: {collection_name} ({count} documents)")
    except Exception as e:
        print(f"Collection: ✗ Error ({e})")

    # Slack
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    app_token = os.environ.get("SLACK_APP_TOKEN", "")
    print(f"\nSlack bot:  {'✓ configured' if bot_token.startswith('xoxb-') else '✗ not set'}")
    print(f"Slack app:  {'✓ configured' if app_token.startswith('xapp-') else '✗ not set'}")

    # Tools
    from tools import TOOL_DEFINITIONS
    print(f"\nTools:      {len(TOOL_DEFINITIONS)} available")
    for t in TOOL_DEFINITIONS:
        print(f"  • {t['function']['name']}: {t['function']['description'][:60]}")

    print()


def main():
    parser = argparse.ArgumentParser(
        prog="openslackbot",
        description="OpenSlackBot — local AI-powered Slack bot with RAG",
    )
    sub = parser.add_subparsers(dest="command")

    # Default: run the bot
    sub.add_parser("bot", help="Start the Slack bot (default)")

    # Ingest
    ingest_parser = sub.add_parser("ingest", help="Ingest files into the knowledge base")
    ingest_parser.add_argument("paths", nargs="+", help="PDF/JSON files or directories")
    ingest_parser.add_argument("--namespace", default="", help="ChromaDB namespace")
    ingest_parser.add_argument("--fields", default=None,
                               help="Comma-separated JSON fields to embed on")

    # Status
    sub.add_parser("status", help="Show bot & RAG status")

    args = parser.parse_args()

    if args.command is None or args.command == "bot":
        cmd_bot(args)
    elif args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "status":
        cmd_status(args)


if __name__ == "__main__":
    main()
