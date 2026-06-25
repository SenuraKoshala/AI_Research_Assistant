import json
import logging
import time

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)


def _build_comparison_prompt(summaries: list[dict]) -> str:
    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += f"""
Paper {i}: {s['title']}
- Problem: {s['problem']}
- Method: {s['method']}
- Datasets: {', '.join(s['datasets']) if s['datasets'] else 'Not specified'}
- Results: {s['results']}
- Limitations: {s['limitations']}
"""

    return f"""You are a research analyst. Compare the following research papers and return a structured JSON comparison.

{summaries_text}

Return ONLY a valid JSON object with exactly this structure:
{{
  "dimensions": {{
    "methodology": {{
      "description": "Overall observation about methodologies used across papers",
      "per_paper": {{
        "Paper title 1": "methodology type and approach",
        "Paper title 2": "methodology type and approach"
      }}
    }},
    "datasets": {{
      "description": "Overall observation about datasets used",
      "per_paper": {{
        "Paper title 1": "datasets used",
        "Paper title 2": "datasets used"
      }}
    }},
    "performance": {{
      "description": "Overall observation about performance results",
      "per_paper": {{
        "Paper title 1": "key metrics and results",
        "Paper title 2": "key metrics and results"
      }}
    }},
    "novelty": {{
      "description": "Overall observation about contributions",
      "per_paper": {{
        "Paper title 1": "key contribution",
        "Paper title 2": "key contribution"
      }}
    }}
  }},
  "research_gaps": ["gap 1", "gap 2", "gap 3"],
  "future_directions": ["direction 1", "direction 2", "direction 3"]
}}

Rules:
- Return JSON only. No explanation, no markdown, no code fences.
- Use the actual paper titles as keys in per_paper.
- Keep descriptions concise.
"""


def _parse_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def compare_papers(summaries: list[dict], llm_calls_used: int = 0) -> tuple[dict, int]:
    """
    Sends all summaries to Gemini and returns a structured comparison.
    Returns (comparison_dict, updated_llm_call_count).
    """
    if not summaries:
        logger.warning("[Comparator] No summaries to compare")
        return {}, llm_calls_used

    logger.info(f"[Comparator] Comparing {len(summaries)} papers")

    prompt = _build_comparison_prompt(summaries)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            parsed = _parse_response(response.text)
            llm_calls_used += 1
            logger.info("[Comparator] Comparison complete")
            return parsed, llm_calls_used

        except Exception as e:
            wait = 2 ** attempt
            logger.warning(f"[Comparator] Attempt {attempt+1} failed: {e} — retrying in {wait}s")
            time.sleep(wait)

    logger.error("[Comparator] All attempts failed — returning empty comparison")
    return {}, llm_calls_used