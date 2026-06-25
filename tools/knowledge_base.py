import json
import logging
import os
from datetime import datetime

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import CHROMA_DIR, SESSIONS_DIR

logger = logging.getLogger(__name__)

# Load embedding model once at module level
_embedder = None

def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        logger.info("[KB] Loading embedding model (all-MiniLM-L6-v2)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _get_chroma_client() -> chromadb.Client:
    return chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )


# ── Save to Knowledge Base ────────────────────────────────────────────────────

def save_to_kb(
    session_id: str,
    topic: str,
    papers: list[dict],
    summaries: list[dict],
    chunks: list[dict],
):
    """
    Embeds all chunks and stores them in ChromaDB.
    Saves full session metadata to sessions/<session_id>.json.
    Skips chunks already stored (idempotent — safe to re-run).
    """
    embedder = _get_embedder()
    client = _get_chroma_client()

    # Each session gets its own ChromaDB collection
    collection_name = f"session_{session_id}"
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"topic": topic, "session_id": session_id},
    )

    if not chunks:
        logger.warning("[KB] No chunks to store")
        return

    # Get already stored IDs to avoid duplicates
    existing = collection.get()["ids"]
    existing_set = set(existing)

    new_chunks = [c for c in chunks if c["chunk_id"] not in existing_set]

    if not new_chunks:
        logger.info("[KB] All chunks already stored — skipping embedding")
    else:
        logger.info(f"[KB] Embedding {len(new_chunks)} new chunks...")

        texts = [c["text"] for c in new_chunks]
        embeddings = embedder.encode(texts, show_progress_bar=True).tolist()

        collection.add(
            ids=[c["chunk_id"] for c in new_chunks],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "paper_id": c["paper_id"],
                    "chunk_index": c["chunk_index"],
                    "session_id": session_id,
                }
                for c in new_chunks
            ],
        )
        logger.info(f"[KB] Stored {len(new_chunks)} chunks in collection '{collection_name}'")

    # Save full session metadata to JSON
    _save_session_metadata(session_id, topic, papers, summaries)


def _save_session_metadata(
    session_id: str,
    topic: str,
    papers: list[dict],
    summaries: list[dict],
):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    metadata = {
        "session_id": session_id,
        "topic": topic,
        "created_at": datetime.now().isoformat(),
        "paper_count": len(papers),
        "papers": papers,
        "summaries": summaries,
    }
    path = os.path.join(SESSIONS_DIR, f"{session_id}_kb.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"[KB] Session metadata saved to {path}")


# ── Query Knowledge Base ──────────────────────────────────────────────────────

def query_kb(
    query: str,
    session_id: str = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Query the knowledge base by semantic similarity.
    If session_id is provided, searches only that session's collection.
    Otherwise searches all collections.
    Returns top_k matching chunks with metadata.
    """
    embedder = _get_embedder()
    client = _get_chroma_client()

    query_embedding = embedder.encode([query]).tolist()

    # Determine which collections to search
    all_collections = client.list_collections()
    if session_id:
        collections = [
            c for c in all_collections
            if c.name == f"session_{session_id}"
        ]
    else:
        collections = all_collections

    if not collections:
        logger.warning("[KB] No collections found to query")
        return []

    results = []
    for collection in collections:
        coll = client.get_collection(collection.name)
        response = coll.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, coll.count()),
            include=["documents", "metadatas", "distances"],
        )

        for doc, meta, dist in zip(
            response["documents"][0],
            response["metadatas"][0],
            response["distances"][0],
        ):
            results.append({
                "text": doc,
                "paper_id": meta.get("paper_id"),
                "session_id": meta.get("session_id"),
                "chunk_index": meta.get("chunk_index"),
                "score": round(1 - dist, 4),  # convert distance to similarity
            })

    # Sort by similarity score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# ── List Past Sessions ────────────────────────────────────────────────────────

def list_kb_sessions() -> list[dict]:
    """Returns metadata for all sessions stored in the knowledge base."""
    sessions = []
    if not os.path.exists(SESSIONS_DIR):
        return sessions

    for fname in os.listdir(SESSIONS_DIR):
        if fname.endswith("_kb.json"):
            path = os.path.join(SESSIONS_DIR, fname)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "session_id": data["session_id"],
                "topic": data["topic"],
                "created_at": data["created_at"],
                "paper_count": data["paper_count"],
            })

    return sessions