import logging
from collections.abc import Iterator

from agent.state import AgentState
from tools.search import search_papers
from tools.pdf_reader import process_papers
from tools.summarizer import summarize_papers
from tools.comparator import compare_papers
from tools.reporter import generate_report
from tools.knowledge_base import save_to_kb
from api.sse import sse

logger = logging.getLogger(__name__)


def run_research_stream(topic: str, max_papers: int = 10) -> Iterator[str]:
    """
    Run the full 7-step research pipeline and yield SSE progress events.

    This mirrors the CLI Orchestrator, but instead of printing to the
    terminal it streams each step's status back to the browser so the UI
    can show a live "thinking" pattern while the session is built.
    """
    try:
        yield sse("status", message=f"Creating a new research session for “{topic}”…")
        state = AgentState(topic=topic)
        state.save()
        yield sse("session", session_id=state.session_id)

        # Step 1 — Search
        yield sse("status", message="🔍 Searching arXiv and Semantic Scholar…")
        papers = search_papers(topic, max_results=max_papers)
        state.papers = [p.to_dict() for p in papers]
        state.mark_step_complete("search_papers")
        yield sse("status", message=f"✓ Found {len(papers)} papers")

        # Steps 2 & 3 — Download + Chunk
        yield sse("status", message="📥 Downloading PDFs and extracting text…")
        download_results, chunks = process_papers(state.papers, state.session_id)
        state.chunks = [c.to_dict() for c in chunks]
        state.mark_step_complete("download_pdfs")
        state.mark_step_complete("chunk_texts")
        success = sum(1 for r in download_results if r.success)
        yield sse("status", message=f"✓ Downloaded {success}/{len(papers)} PDFs · {len(chunks)} text chunks")

        # Step 4 — Summarize
        yield sse("status", message="📝 Summarizing papers with Gemini…")
        summaries, call_count = summarize_papers(
            papers=state.papers,
            chunks=state.chunks,
            llm_calls_used=state.llm_calls,
        )
        state.summaries = [s.to_dict() for s in summaries]
        state.llm_calls = call_count
        state.mark_step_complete("summarize_papers")
        yield sse("status", message=f"✓ Summarized {len(summaries)} papers")

        # Step 5 — Compare
        yield sse("status", message="🔬 Comparing papers and finding research gaps…")
        comparison, call_count = compare_papers(
            summaries=state.summaries,
            llm_calls_used=state.llm_calls,
        )
        state.comparison = comparison
        state.llm_calls = call_count
        state.mark_step_complete("compare_papers")
        yield sse("status", message="✓ Comparison complete")

        # Step 6 — Report
        yield sse("status", message="📄 Generating the final report…")
        report_path = generate_report(
            topic=topic,
            summaries=state.summaries,
            comparison=state.comparison,
            session_id=state.session_id,
        )
        state.report_path = report_path
        state.mark_step_complete("generate_report")
        yield sse("status", message="✓ Report generated")

        # Step 7 — Save to knowledge base
        yield sse("status", message="💾 Embedding chunks into the knowledge base…")
        save_to_kb(
            session_id=state.session_id,
            topic=topic,
            papers=state.papers,
            summaries=state.summaries,
            chunks=state.chunks,
        )
        state.mark_step_complete("save_to_kb")
        yield sse("status", message=f"✓ Saved {len(chunks)} chunks to the knowledge base")

        yield sse(
            "done",
            session_id=state.session_id,
            topic=topic,
            paper_count=len(papers),
        )

    except Exception as e:  # noqa: BLE001 — surface any failure to the UI
        logger.exception("[Research] Pipeline failed")
        yield sse("error", message=str(e))