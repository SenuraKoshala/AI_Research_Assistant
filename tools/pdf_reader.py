import logging
import os
import re
import time
from dataclasses import dataclass, asdict

import fitz  # PyMuPDF
import requests

from config import CHUNK_SIZE, CHUNK_OVERLAP, SESSIONS_DIR

logger = logging.getLogger(__name__)


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    chunk_id: str        # "{paper_id}_chunk_{index}"
    paper_id: str
    chunk_index: int
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DownloadResult:
    paper_id: str
    title: str
    success: bool
    text: str = ""
    error: str = ""


# ── PDF Download ──────────────────────────────────────────────────────────────

def download_pdf(pdf_url: str, paper_id: str) -> str:
    """
    Downloads a PDF from the given URL and extracts full text using PyMuPDF.
    Returns the extracted text string.
    Raises an exception on failure — caller should catch and skip.
    """
    headers = {"User-Agent": "Mozilla/5.0 (research-assistant-bot/1.0)"}

    logger.info(f"  Downloading: {pdf_url[:80]}")
    response = requests.get(pdf_url, headers=headers, timeout=30, stream=True)
    response.raise_for_status()

    # Check it's actually a PDF
    content_type = response.headers.get("Content-Type", "")
    if "pdf" not in content_type and not pdf_url.endswith(".pdf"):
        raise ValueError(f"URL does not appear to be a PDF: {content_type}")

    # Load PDF from bytes directly — no temp file needed
    pdf_bytes = response.content
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()

    full_text = "\n".join(pages_text)
    full_text = _clean_text(full_text)

    if not full_text.strip():
        raise ValueError("PDF extracted text is empty — may be scanned/image-only")

    logger.info(f"  Extracted {len(full_text)} characters from PDF")
    return full_text


def _clean_text(text: str) -> str:
    """Remove excessive whitespace and non-printable characters."""
    text = re.sub(r'\n{3,}', '\n\n', text)       # collapse 3+ newlines
    text = re.sub(r'[ \t]{2,}', ' ', text)        # collapse multiple spaces
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)  # remove non-ASCII
    return text.strip()


# ── Text Chunking ─────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    paper_id: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    Splits text into overlapping word-based chunks.
    chunk_size and overlap are in approximate word counts
    (close enough to token counts for most English text).
    """
    words = text.split()
    chunks = []
    start = 0
    index = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)

        chunks.append(Chunk(
            chunk_id=f"{paper_id}_chunk_{index}",
            paper_id=paper_id,
            chunk_index=index,
            text=chunk_text_str,
        ))

        index += 1
        start += chunk_size - overlap  # slide forward with overlap

    logger.info(f"  Chunked into {len(chunks)} chunks (paper: {paper_id})")
    return chunks


# ── Batch Runner ──────────────────────────────────────────────────────────────

def process_papers(papers: list[dict], session_id: str) -> tuple[list[DownloadResult], list[Chunk]]:
    """
    Downloads and chunks all papers.
    Skips failures gracefully.
    Returns (results, all_chunks).
    """
    all_results: list[DownloadResult] = []
    all_chunks: list[Chunk] = []

    for i, paper in enumerate(papers):
        paper_id = paper["paper_id"]
        title = paper["title"]
        pdf_url = paper["pdf_url"]

        logger.info(f"[PDF {i+1}/{len(papers)}] {title[:70]}")

        try:
            text = download_pdf(pdf_url, paper_id)
            chunks = chunk_text(text, paper_id)

            all_chunks.extend(chunks)
            all_results.append(DownloadResult(
                paper_id=paper_id,
                title=title,
                success=True,
                text=text,
            ))

            # Save raw text to disk per paper
            _save_paper_text(session_id, paper_id, text)

        except Exception as e:
            logger.warning(f"  Skipping '{title[:60]}': {e}")
            all_results.append(DownloadResult(
                paper_id=paper_id,
                title=title,
                success=False,
                error=str(e),
            ))

        time.sleep(1.0)  # polite delay between downloads

    success_count = sum(1 for r in all_results if r.success)
    logger.info(f"Downloaded {success_count}/{len(papers)} papers successfully")

    return all_results, all_chunks


def _save_paper_text(session_id: str, paper_id: str, text: str):
    """Save extracted text to sessions/<session_id>/texts/<paper_id>.txt"""
    folder = os.path.join(SESSIONS_DIR, session_id, "texts")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{paper_id}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)