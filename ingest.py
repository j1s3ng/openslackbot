"""CLI tool to ingest PDFs and JSON files into Pinecone for RAG.

Usage:
    python ingest.py document.pdf
    python ingest.py data.json --fields title,body
    python ingest.py ./docs/ --namespace project-docs
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest files into Pinecone for RAG")
    parser.add_argument("paths", nargs="+", help="PDF or JSON file(s), or directories")
    parser.add_argument("--namespace", default="", help="Pinecone namespace")
    parser.add_argument("--fields", default=None,
                        help="Comma-separated JSON field names to extract (JSON only)")
    args = parser.parse_args()

    from rag import ingest_pdf, ingest_json

    text_fields = [f.strip() for f in args.fields.split(",")] if args.fields else None
    total = 0

    for p in args.paths:
        path = Path(p)
        files = list(path.rglob("*")) if path.is_dir() else [path]

        for file in files:
            suffix = file.suffix.lower()
            if suffix == ".pdf":
                n = ingest_pdf(str(file), namespace=args.namespace)
                total += n
                logger.info("  ✓ %s → %d chunks", file.name, n)
            elif suffix == ".json":
                n = ingest_json(str(file), text_fields=text_fields,
                                namespace=args.namespace)
                total += n
                logger.info("  ✓ %s → %d chunks", file.name, n)
            else:
                logger.warning("  Skipping unsupported file: %s", file.name)

    logger.info("Done — %d total chunks ingested.", total)


if __name__ == "__main__":
    main()
