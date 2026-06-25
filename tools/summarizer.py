import json
import logging
import time
from dataclasses import dataclass, asdict

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_LLM_CALLS_PER_SESSION

client = genai.Client(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class PaperSummary:
    paper_id: str
    title: str
    problem: str
    method: str
    datasets: list[str]
    results: str
    limitations: str

    def to_dict(self) -> dict:
        return asdict(self)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _group_chunks_by_paper(chunks: list[dict]) -> dict[str, list[str]]:
    """Group chunk texts by paper_id."""
    grouped: dict[str, list[str]] = {}
    for chunk in chunks:
        pid = chunk["paper_id"]
        grouped.setdefault(pid, [])
        grouped[pid].append(chunk["text"])
    return grouped


def _build_prompt(title: str, chunks: list[str]) -> str:
    # Use first 6 chunks to stay within context limits
    combined = "\n\n".join(chunks[:6])
    return f"""You are a research paper analyst. Read the following excerpt from a research paper and extract structured information.

Paper title: {title}

Paper content:
{combined}

Return ONLY a valid JSON object with exactly these fields:
{{
  "problem": "The research problem or gap this paper addresses",
  "method": "The proposed method, model, or approach",
  "datasets": ["dataset1", "dataset2"],
  "results": "Key quantitative results and metrics reported",
  "limitations": "Limitations acknowledged by the authors"
}}

Rules:
- Return JSON only. No explanation, no markdown, no code fences.
- If a field cannot be determined from the text, use "Not specified".
- Keep each field concise (2-3 sentences max).
- datasets must be a JSON array of strings.
"""


def _parse_response(response_text: str) -> dict:
    """Safely parse LLM JSON response."""
    # Strip markdown fences if model ignores instructions
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _call_gemini(prompt: str) -> str:
    """Single Gemini API call with basic retry."""
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(f"[Gemini] Attempt {attempt+1} failed: {e} — retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("Gemini API failed after 3 attempts")

# ── Main Entry Point ──────────────────────────────────────────────────────────

def summarize_papers(
    papers: list[dict],
    chunks: list[dict],
    llm_calls_used: int = 0,
) -> tuple[list[PaperSummary], int]:
    """
    Summarizes each paper using its chunks.
    Respects MAX_LLM_CALLS_PER_SESSION cap.
    Returns (summaries, updated_llm_call_count).
    """
    grouped = _group_chunks_by_paper(chunks)
    summaries: list[PaperSummary] = []
    call_count = llm_calls_used

    # Build a title lookup
    title_map = {p["paper_id"]: p["title"] for p in papers}

    for paper_id, paper_chunks in grouped.items():
        title = title_map.get(paper_id, "Unknown")

        if call_count >= MAX_LLM_CALLS_PER_SESSION:
            logger.warning(f"[Summarizer] LLM call cap reached ({MAX_LLM_CALLS_PER_SESSION}) — stopping")
            break

        logger.info(f"[Summarizer] Summarizing: {title[:70]}")

        try:
            prompt = _build_prompt(title, paper_chunks)
            raw = _call_gemini(prompt)
            call_count += 1
            parsed = _parse_response(raw)

            summary = PaperSummary(
                paper_id=paper_id,
                title=title,
                problem=parsed.get("problem", "Not specified"),
                method=parsed.get("method", "Not specified"),
                datasets=parsed.get("datasets", []),
                results=parsed.get("results", "Not specified"),
                limitations=parsed.get("limitations", "Not specified"),
            )
            summaries.append(summary)
            logger.info(f"  ✓ Summary complete for: {title[:60]}")

        except Exception as e:
            logger.error(f"  ✗ Failed to summarize '{title[:60]}': {e}")
            # Add a placeholder so we don't lose the paper entirely
            summaries.append(PaperSummary(
                paper_id=paper_id,
                title=title,
                problem="Summarization failed",
                method="Summarization failed",
                datasets=[],
                results="Summarization failed",
                limitations=str(e),
            ))

        time.sleep(1.0)  # avoid hammering Gemini

    logger.info(f"[Summarizer] Done. {len(summaries)} summaries. LLM calls used: {call_count}")
    return summaries, call_count