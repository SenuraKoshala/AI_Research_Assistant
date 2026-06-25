import logging
import typer
from rich.console import Console
from rich.table import Table

from agent.state import AgentState
from agent.orchestrator import Orchestrator

app = typer.Typer(help="AI Research Assistant — Agentic research pipeline")
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler(),
    ],
)


@app.command()
def research(
    topic: str = typer.Argument(..., help="Research topic to investigate"),
    max_papers: int = typer.Option(10, help="Max papers to retrieve"),
    resume: str = typer.Option(None, help="Resume by session ID"),
):
    """Start or resume a research session."""
    if resume:
        console.print(f"[cyan]Resuming session:[/cyan] {resume}")
        state = AgentState.load(resume)
    else:
        state = AgentState(topic=topic)
        state.save()
        console.print(f"[cyan]New session created:[/cyan] {state.session_id}")

    orchestrator = Orchestrator(state)
    orchestrator.run()


@app.command()
def sessions():
    """List all past research sessions."""
    all_sessions = AgentState.list_sessions()
    if not all_sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    table = Table(title="Past Research Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Topic")
    table.add_column("Created")
    table.add_column("Steps Done")

    for s in all_sessions:
        table.add_row(
            s["session_id"],
            s["topic"],
            s["created_at"][:19],
            f"{len(s['completed_steps'])}/7",
        )
    console.print(table)

@app.command()
def query(
    q: str = typer.Argument(..., help="Query to search the knowledge base"),
    session_id: str = typer.Option(None, help="Limit search to a specific session"),
    top_k: int = typer.Option(5, help="Number of results to return"),
):
    """Query the knowledge base across past research sessions."""
    from tools.knowledge_base import query_kb

    console.print(f"\n[bold cyan]Querying KB:[/bold cyan] {q}\n")
    results = query_kb(query=q, session_id=session_id, top_k=top_k)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    for i, r in enumerate(results, 1):
        console.print(f"[bold]{i}. Score: {r['score']}[/bold] | Paper: {r['paper_id']}")
        console.print(f"   {r['text'][:200]}...")
        console.print()


@app.command()
def kb_sessions():
    """List all sessions stored in the knowledge base."""
    from tools.knowledge_base import list_kb_sessions

    all_sessions = list_kb_sessions()
    if not all_sessions:
        console.print("[yellow]No KB sessions found.[/yellow]")
        return

    table = Table(title="Knowledge Base Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Topic")
    table.add_column("Created")
    table.add_column("Papers")

    for s in all_sessions:
        table.add_row(
            s["session_id"],
            s["topic"],
            s["created_at"][:19],
            str(s["paper_count"]),
        )
    console.print(table)


if __name__ == "__main__":
    app()