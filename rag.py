import os
import json
import logging
from pathlib import Path

import chromadb
from openai import OpenAI

logger = logging.getLogger(__name__)

# Embedding model served by LM Studio (or override with a dedicated endpoint)
_embed_client = OpenAI(
    base_url=os.environ.get("EMBEDDING_BASE_URL",
                            os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")),
    api_key="lm-studio",
    timeout=120.0,
)

EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "2048"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "128"))
TOP_K = int(os.environ.get("RAG_TOP_K", "5"))

# Local ChromaDB storage — all data stays on disk, no external services
CHROMA_DIR = os.environ.get("CHROMA_DIR", "./chroma_data")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "openslackbot")

_chroma_client = None
_collection = None


def _get_collection():
    """Lazy-init the local ChromaDB collection."""
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection '%s' at %s (%d docs)",
                    CHROMA_COLLECTION, CHROMA_DIR, _collection.count())
    return _collection


# ── Embedding ────────────────────────────────────────────────────────────────

def embed(texts: list[str]) -> list[list[float]]:
    """Get embeddings from LM Studio's embedding endpoint."""
    response = _embed_client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in response.data]


# ── Chunking ─────────────────────────────────────────────────────────────────

def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


# ── PDF ingestion ────────────────────────────────────────────────────────────

def ingest_pdf(file_path: str, namespace: str = "") -> int:
    """Extract text from a PDF, chunk it, embed, and upsert to Pinecone."""
    import PyPDF2

    path = Path(file_path)
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((i + 1, text))

    chunks = []
    for page_num, page_text in pages:
        for j, chunk in enumerate(_chunk_text(page_text)):
            chunks.append({
                "id": f"{path.stem}_p{page_num}_c{j}",
                "text": chunk,
                "metadata": {
                    "source": path.name,
                    "page": page_num,
                    "chunk": j,
                    "type": "pdf",
                },
            })

    _upsert_chunks(chunks, namespace)
    logger.info("Ingested %d chunks from PDF: %s", len(chunks), path.name)
    return len(chunks)


# ── JSON ingestion ───────────────────────────────────────────────────────────

def ingest_json(file_path: str, text_fields: list[str] | None = None,
                namespace: str = "") -> int:
    """Ingest a JSON file into ChromaDB.

    Each JSON record is stored as a complete, intact document — no chunking.
    The embedding is generated from key text fields for retrieval, but the
    full raw JSON is what gets stored and returned to the model.

    Handles both a single JSON object and a list of objects.
    `text_fields` specifies which keys to embed on; if None, all string
    values are used for the embedding.
    """
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    docs = []
    for i, record in enumerate(data):
        # Text used for embedding (retrieval matching)
        parts = _extract_strings(record, text_fields)
        embed_text = "\n".join(parts)
        if not embed_text.strip():
            continue

        # Full JSON stored as the document (what the model actually sees)
        record_json = json.dumps(record, ensure_ascii=False, indent=2)

        docs.append({
            "id": f"{path.stem}_r{i}",
            "text": record_json,
            "embed_text": embed_text,
            "metadata": {
                "source": path.name,
                "record": i,
                "type": "json",
            },
        })

    _upsert_docs(docs, namespace)
    logger.info("Ingested %d records from JSON: %s", len(docs), path.name)
    return len(docs)


def _extract_strings(obj, text_fields: list[str] | None) -> list[str]:
    """Recursively pull string values from a dict/list."""
    parts = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            if text_fields and key not in text_fields:
                continue
            if isinstance(val, str) and val.strip():
                parts.append(val)
            elif isinstance(val, (dict, list)):
                parts.extend(_extract_strings(val, None))
    elif isinstance(obj, list):
        for item in obj:
            parts.extend(_extract_strings(item, text_fields))
    return parts


# ── Upsert ───────────────────────────────────────────────────────────────────

def _upsert_chunks(chunks: list[dict], namespace: str) -> None:
    """Embed chunks and upsert into local ChromaDB."""
    if not chunks:
        return
    collection = _get_collection()
    batch_size = 96
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        vectors = embed(texts)
        ids = [c["id"] for c in batch]
        metadatas = [{**c["metadata"], "namespace": namespace} for c in batch]
        collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas,
        )


def _upsert_docs(docs: list[dict], namespace: str) -> None:
    """Embed docs on their embed_text (key fields) but store the full text.

    Used for JSON records where the embedding should match on extracted text
    but the stored document is the complete raw JSON.
    """
    if not docs:
        return
    collection = _get_collection()
    batch_size = 96
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        # Embed on the extracted text fields, not the full JSON
        embed_texts = [d["embed_text"] for d in batch]
        vectors = embed(embed_texts)
        ids = [d["id"] for d in batch]
        # Store the full JSON as the document
        documents = [d["text"] for d in batch]
        metadatas = [{**d["metadata"], "namespace": namespace} for d in batch]
        collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=documents,
            metadatas=metadatas,
        )


# ── Query / Retrieval ────────────────────────────────────────────────────────

def retrieve(query: str, namespace: str = "", top_k: int | None = None) -> list[dict]:
    """Embed the query and retrieve the top-k most relevant chunks."""
    k = top_k or TOP_K
    collection = _get_collection()
    query_vec = embed([query])[0]

    where_filter = {"namespace": namespace} if namespace else None
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    docs = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        docs.append({
            "text": doc,
            "source": meta.get("source", ""),
            "score": 1 - dist,  # cosine distance → similarity
        })
    return docs


def build_context(query: str, namespace: str = "") -> str:
    """Retrieve relevant chunks and format them as context for the LLM."""
    docs = retrieve(query, namespace=namespace)
    if not docs:
        return ""
    parts = []
    for i, doc in enumerate(docs, 1):
        parts.append(f"[{i}] (source: {doc['source']}, relevance: {doc['score']:.2f})\n{doc['text']}")
    return "\n\n".join(parts)
