import hashlib
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from config import MAX_PAPERS, TAVILY_API_KEY, S2_API_KEY

import arxiv
import requests

from config import MAX_PAPERS, TAVILY_API_KEY

logger = logging.getLogger(__name__)


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class PaperMetadata:
    paper_id: str           # SHA256 of pdf_url
    title: str
    authors: list[str]
    year: int
    abstract: str
    pdf_url: str
    source: str             # "arXiv" | "SemanticScholar" | "Tavily"

    def to_dict(self) -> dict:
        return asdict(self)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_id(url: str) -> str:
    """Stable paper ID from its PDF URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _is_duplicate(paper: PaperMetadata, seen: list[PaperMetadata]) -> bool:
    """Deduplicate by title similarity (lowercased exact match for now)."""
    normalized = paper.title.lower().strip()
    return any(normalized == s.title.lower().strip() for s in seen)


# ── arXiv Search ──────────────────────────────────────────────────────────────

def _search_arxiv(topic: str, max_results: int) -> list[PaperMetadata]:
    logger.info(f"[arXiv] Searching: '{topic}'")
    papers = []

    try:
        time.sleep(3.0)  # arXiv requires polite delay
        client = arxiv.Client(num_retries=2, delay_seconds=5.0)
        search = arxiv.Search(
            query=topic,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        for result in client.results(search):
            pdf_url = result.pdf_url
            if not pdf_url:
                continue
            paper = PaperMetadata(
                paper_id=_make_id(pdf_url),
                title=result.title,
                authors=[a.name for a in result.authors],
                year=result.published.year,
                abstract=result.summary.replace("\n", " "),
                pdf_url=pdf_url,
                source="arXiv",
            )
            papers.append(paper)
            logger.info(f"  [arXiv] Found: {result.title[:70]}")
            time.sleep(0.5)

    except Exception as e:
        logger.error(f"[arXiv] Search failed: {e}")

    return papers


# ── Semantic Scholar Search ───────────────────────────────────────────────────

def _search_semantic_scholar(topic: str, max_results: int) -> list[PaperMetadata]:
    logger.info(f"[SemanticScholar] Searching: '{topic}'")
    papers = []

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": topic,
        "limit": max_results,
        "fields": "title,authors,year,abstract,openAccessPdf,externalIds",
    }
    headers = {"x-api-key": S2_API_KEY} if S2_API_KEY else {}

    # Retry with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)

            if response.status_code == 429:
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"[S2] Rate limited — retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue

            response.raise_for_status()
            data = response.json()

            for item in data.get("data", []):
                pdf_info = item.get("openAccessPdf")
                if not pdf_info or not pdf_info.get("url"):
                    continue
                pdf_url = pdf_info["url"]
                paper = PaperMetadata(
                    paper_id=_make_id(pdf_url),
                    title=item.get("title", "Unknown"),
                    authors=[a["name"] for a in item.get("authors", [])],
                    year=item.get("year") or 0,
                    abstract=(item.get("abstract") or "").replace("\n", " "),
                    pdf_url=pdf_url,
                    source="SemanticScholar",
                )
                papers.append(paper)
                logger.info(f"  [S2] Found: {item.get('title', '')[:70]}")
                time.sleep(1.0)

            break  # success — exit retry loop

        except Exception as e:
            logger.error(f"[SemanticScholar] Search failed: {e}")
            break

    return papers


# ── Tavily Fallback ───────────────────────────────────────────────────────────

def _search_tavily(topic: str, max_results: int) -> list[PaperMetadata]:
    logger.info(f"[Tavily] Fallback search: '{topic}'")
    papers = []

    if not TAVILY_API_KEY:
        logger.warning("[Tavily] No API key set — skipping fallback")
        return papers

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": f"{topic} research paper filetype:pdf",
                "max_results": max_results,
                "search_depth": "advanced",
            },
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results", [])

        for item in results:
            url = item.get("url", "")
            title = item.get("title", "Unknown")
            paper = PaperMetadata(
                paper_id=_make_id(url),
                title=title,
                authors=[],
                year=0,
                abstract=item.get("content", ""),
                pdf_url=url,
                source="Tavily",
            )
            papers.append(paper)
            logger.info(f"  [Tavily] Found: {title[:70]}")

    except Exception as e:
        logger.error(f"[Tavily] Search failed: {e}")

    return papers


# ── Main Entry Point ──────────────────────────────────────────────────────────

def search_papers(topic: str, max_results: int = MAX_PAPERS) -> list[PaperMetadata]:
    """
    Search arXiv and Semantic Scholar for papers on the given topic.
    Deduplicates results. Falls back to Tavily if both return nothing.

    Returns a list of PaperMetadata (up to max_results).
    """
    all_papers: list[PaperMetadata] = []
    half = max_results // 2

    # Primary sources
    arxiv_results = _search_arxiv(topic, half)
    s2_results = _search_semantic_scholar(topic, half)

    # Merge with deduplication
    for paper in arxiv_results + s2_results:
        if not _is_duplicate(paper, all_papers):
            all_papers.append(paper)

    # Fallback if both sources returned nothing
    if not all_papers:
        logger.warning("No results from arXiv or S2 — trying Tavily fallback")
        all_papers = _search_tavily(topic, max_results)

    logger.info(f"Total papers found: {len(all_papers)}")
    return all_papers[:max_results]