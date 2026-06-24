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


if __name__ == "__main__":
    app()