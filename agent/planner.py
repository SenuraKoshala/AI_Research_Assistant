from agent.state import STEPS


def generate_plan(topic: str) -> list[dict]:
    descriptions = {
        "search_papers":    f'Search arXiv & Semantic Scholar for papers on "{topic}"',
        "download_pdfs":    "Download PDFs for each paper found",
        "chunk_texts":      "Split each PDF into overlapping text chunks",
        "summarize_papers": "Summarize each paper (problem, method, datasets, results)",
        "compare_papers":   "Compare all papers across methodology, datasets, and metrics",
        "generate_report":  "Generate a structured Markdown research report",
        "save_to_kb":       "Embed chunks and save session to the knowledge base",
    }
    return [
        {"step": i + 1, "name": step, "description": descriptions[step]}
        for i, step in enumerate(STEPS)
    ]