import logging
import os
from datetime import datetime

from config import REPORTS_DIR

logger = logging.getLogger(__name__)


def generate_report(
    topic: str,
    summaries: list[dict],
    comparison: dict,
    session_id: str,
) -> str:
    """
    Compiles summaries and comparison into a structured Markdown report.
    Saves to reports/<session_id>.md and returns the file path.
    """
    lines = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines += [
        f"# Research Report: {topic}",
        f"",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Session ID:** {session_id}  ",
        f"**Papers Reviewed:** {len(summaries)}",
        f"",
    ]

    # ── Executive Summary ─────────────────────────────────────────────────────
    lines += [
        "## Executive Summary",
        "",
        f"This report summarizes {len(summaries)} research papers on the topic of "
        f"**{topic}**. The papers were automatically retrieved, parsed, and analyzed "
        f"using an agentic AI pipeline.",
        "",
    ]

    # ── Methodology Comparison Table ──────────────────────────────────────────
    lines += [
        "## Methodology Comparison",
        "",
    ]

    if comparison and "dimensions" in comparison:
        dims = comparison["dimensions"]

        # Build table header
        lines += [
            "| Paper | Methodology | Datasets | Results | Novelty |",
            "|-------|-------------|----------|---------|---------|",
        ]

        # Collect all paper titles from per_paper keys
        all_titles = set()
        for dim in dims.values():
            all_titles.update(dim.get("per_paper", {}).keys())

        for title in all_titles:
            methodology = dims.get("methodology", {}).get("per_paper", {}).get(title, "N/A")
            datasets = dims.get("datasets", {}).get("per_paper", {}).get(title, "N/A")
            performance = dims.get("performance", {}).get("per_paper", {}).get(title, "N/A")
            novelty = dims.get("novelty", {}).get("per_paper", {}).get(title, "N/A")

            # Truncate long cells for readability
            short_title = title[:50] + "..." if len(title) > 50 else title
            lines.append(
                f"| {short_title} | {methodology[:60]} | {datasets[:40]} | {performance[:60]} | {novelty[:60]} |"
            )

        lines.append("")

        # Dimension summaries
        lines += ["### Key Observations", ""]
        for dim_name, dim_data in dims.items():
            desc = dim_data.get("description", "")
            if desc:
                lines.append(f"**{dim_name.capitalize()}:** {desc}")
                lines.append("")

    else:
        lines += ["*Comparison data not available.*", ""]

    # ── Per-Paper Summaries ───────────────────────────────────────────────────
    lines += ["## Paper Summaries", ""]

    for i, s in enumerate(summaries, 1):
        lines += [
            f"### {i}. {s['title']}",
            "",
            f"**Problem:** {s['problem']}",
            "",
            f"**Method:** {s['method']}",
            "",
            f"**Datasets:** {', '.join(s['datasets']) if s['datasets'] else 'Not specified'}",
            "",
            f"**Results:** {s['results']}",
            "",
            f"**Limitations:** {s['limitations']}",
            "",
            "---",
            "",
        ]

    # ── Research Gaps ─────────────────────────────────────────────────────────
    if comparison and "research_gaps" in comparison:
        lines += ["## Research Gaps", ""]
        for gap in comparison["research_gaps"]:
            lines.append(f"- {gap}")
        lines.append("")

    # ── Future Directions ─────────────────────────────────────────────────────
    if comparison and "future_directions" in comparison:
        lines += ["## Future Directions", ""]
        for direction in comparison["future_directions"]:
            lines.append(f"- {direction}")
        lines.append("")

    # ── References ────────────────────────────────────────────────────────────
    lines += ["## References", ""]
    for i, s in enumerate(summaries, 1):
        lines.append(f"{i}. {s['title']}")
    lines.append("")

    # ── Save to disk ──────────────────────────────────────────────────────────
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"{session_id}.md")

    report_text = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    logger.info(f"[Reporter] Report saved to {report_path}")
    return report_path