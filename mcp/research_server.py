import asyncio
import json
import logging
import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from tools.search import search_papers
from tools.knowledge_base import query_kb, list_kb_sessions
from tools.summarizer import summarize_papers
from tools.reporter import generate_report
from tools.pdf_reader import process_papers
from tools.comparator import compare_papers
from agent.state import AgentState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("research-assistant")


# ── Tool: search_papers ───────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_papers",
            description="Search arXiv and Semantic Scholar for academic papers on a given topic. Returns paper titles, authors, abstracts and PDF URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The research topic to search for",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of papers to return (default 10)",
                        "default": 10,
                    },
                },
                "required": ["topic"],
            },
        ),
        types.Tool(
            name="query_knowledge_base",
            description="Query the research knowledge base using semantic search. Returns relevant chunks from previously researched papers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or topic to search for in the knowledge base",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID to limit search to a specific research session",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="list_sessions",
            description="List all past research sessions stored in the knowledge base, with their topics and paper counts.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="run_research_pipeline",
            description="Run the full research pipeline on a topic: search papers, download PDFs, summarize, compare, and generate a report. This is a long-running operation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The research topic to investigate",
                    },
                    "max_papers": {
                        "type": "integer",
                        "description": "Maximum papers to process (default 10)",
                        "default": 10,
                    },
                },
                "required": ["topic"],
            },
        ),
        types.Tool(
            name="get_session_report",
            description="Get the generated Markdown research report for a specific session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to get the report for",
                    },
                },
                "required": ["session_id"],
            },
        ),
    ]


# ── Tool Handlers ─────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    if name == "search_papers":
        topic = arguments["topic"]
        max_results = arguments.get("max_results", 10)

        papers = search_papers(topic, max_results=max_results)
        result = [
            {
                "title": p.title,
                "authors": p.authors[:3],  # first 3 authors
                "year": p.year,
                "abstract": p.abstract[:300],
                "pdf_url": p.pdf_url,
                "source": p.source,
            }
            for p in papers
        ]
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2),
        )]

    elif name == "query_knowledge_base":
        query = arguments["query"]
        session_id = arguments.get("session_id")
        top_k = arguments.get("top_k", 5)

        results = query_kb(query=query, session_id=session_id, top_k=top_k)
        return [types.TextContent(
            type="text",
            text=json.dumps(results, indent=2),
        )]

    elif name == "list_sessions":
        sessions = list_kb_sessions()
        return [types.TextContent(
            type="text",
            text=json.dumps(sessions, indent=2),
        )]

    elif name == "run_research_pipeline":
        topic = arguments["topic"]
        max_papers = arguments.get("max_papers", 10)

        # Create a new session state
        state = AgentState(topic=topic)
        state.save()

        results = {"session_id": state.session_id, "steps": []}

        try:
            # Step 1 — Search
            papers = search_papers(topic, max_results=max_papers)
            state.papers = [p.to_dict() for p in papers]
            state.mark_step_complete("search_papers")
            results["steps"].append(f"✓ Found {len(papers)} papers")

            # Step 2 & 3 — Download + Chunk
            download_results, chunks = process_papers(state.papers, state.session_id)
            state.chunks = [c.to_dict() for c in chunks]
            state.mark_step_complete("download_pdfs")
            state.mark_step_complete("chunk_texts")
            success = sum(1 for r in download_results if r.success)
            results["steps"].append(f"✓ Downloaded {success}/{len(papers)} PDFs, {len(chunks)} chunks")

            # Step 4 — Summarize
            summaries, call_count = summarize_papers(
                papers=state.papers,
                chunks=state.chunks,
                llm_calls_used=state.llm_calls,
            )
            state.summaries = [s.to_dict() for s in summaries]
            state.llm_calls = call_count
            state.mark_step_complete("summarize_papers")
            results["steps"].append(f"✓ Summarized {len(summaries)} papers")

            # Step 5 — Compare
            comparison, call_count = compare_papers(
                summaries=state.summaries,
                llm_calls_used=state.llm_calls,
            )
            state.comparison = comparison
            state.llm_calls = call_count
            state.mark_step_complete("compare_papers")
            results["steps"].append("✓ Comparison complete")

            # Step 6 — Report
            report_path = generate_report(
                topic=topic,
                summaries=state.summaries,
                comparison=state.comparison,
                session_id=state.session_id,
            )
            state.report_path = report_path
            state.mark_step_complete("generate_report")
            results["steps"].append(f"✓ Report saved to {report_path}")

            # Step 7 — Save to KB
            from tools.knowledge_base import save_to_kb
            save_to_kb(
                session_id=state.session_id,
                topic=topic,
                papers=state.papers,
                summaries=state.summaries,
                chunks=state.chunks,
            )
            state.mark_step_complete("save_to_kb")
            results["steps"].append(f"✓ Saved {len(chunks)} chunks to knowledge base")

            results["status"] = "complete"

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            logger.error(f"[MCP] Pipeline failed: {e}")

        return [types.TextContent(
            type="text",
            text=json.dumps(results, indent=2),
        )]

    elif name == "get_session_report":
        session_id = arguments["session_id"]
        report_path = os.path.join("reports", f"{session_id}.md")

        if not os.path.exists(report_path):
            return [types.TextContent(
                type="text",
                text=f"No report found for session {session_id}",
            )]

        with open(report_path, encoding="utf-8") as f:
            content = f.read()

        return [types.TextContent(type="text", text=content)]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ── Entry Point ───────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())