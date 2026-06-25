import logging
from rich.console import Console
from rich.table import Table

from agent.state import AgentState
from agent.planner import generate_plan
from tools.search import search_papers
from tools.pdf_reader import process_papers
from tools.summarizer import summarize_papers
from tools.comparator import compare_papers
from tools.reporter import generate_report

console = Console()
logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, state: AgentState):
        self.state = state

    def show_plan(self):
        plan = generate_plan(self.state.topic)
        console.print(f"\n[bold cyan]Research Plan:[/bold cyan] {self.state.topic}")
        console.print(f"[dim]Session ID: {self.state.session_id}[/dim]\n")
        for item in plan:
            done = item["name"] in self.state.completed_steps
            icon = "[green]✓[/green]" if done else "[yellow]○[/yellow]"
            console.print(f"  {icon} Step {item['step']}: {item['description']}")
        console.print()

    def run(self):
        self.show_plan()
        console.print("[bold]Starting research agent...[/bold]\n")

        while True:
            next_step = self.state.next_pending_step()
            if next_step is None:
                console.print("[bold green]✓ All steps complete![/bold green]")
                break

            console.print(f"[bold blue]→ Running:[/bold blue] {next_step}")
            self.state.current_step = next_step

            try:
                self._run_step(next_step)
                self.state.mark_step_complete(next_step)
                console.print(f"[green]  ✓ {next_step} complete[/green]\n")
            except NotImplementedError:
                console.print(f"[yellow]  ⚠ {next_step} — not yet implemented, skipping[/yellow]\n")
                self.state.mark_step_complete(next_step)
            except Exception as e:
                logger.error(f"Step {next_step} failed: {e}")
                self.state.mark_step_failed(next_step)
                console.print(f"[red]  ✗ {next_step} failed: {e}[/red]\n")
                break

    def _run_step(self, step: str):
        if step == "search_papers":
            papers = search_papers(self.state.topic)
            self.state.papers = [p.to_dict() for p in papers]
            self._display_papers(papers)

        elif step == "download_pdfs":
            results, chunks = process_papers(
                self.state.papers,
                self.state.session_id,
            )
            # Save chunks to state as dicts
            self.state.chunks = [c.to_dict() for c in chunks]
            self._display_download_results(results)

        elif step == "chunk_texts":
            # Chunking is done inside process_papers, so nothing extra needed
            total = len(getattr(self.state, "chunks", []))
            console.print(f"  [dim]Total chunks ready: {total}[/dim]")

        elif step == "summarize_papers":
            summaries, call_count = summarize_papers(
                papers=self.state.papers,
                chunks=self.state.chunks,
                llm_calls_used=self.state.llm_calls,
            )
            self.state.summaries = [s.to_dict() for s in summaries]
            self.state.llm_calls = call_count
            self._display_summaries(summaries)
        elif step == "compare_papers":
            comparison, call_count = compare_papers(
                summaries=self.state.summaries,
                llm_calls_used=self.state.llm_calls,
            )
            self.state.comparison = comparison
            self.state.llm_calls = call_count
            self._display_comparison(comparison)

        elif step == "generate_report":
            report_path = generate_report(
                topic=self.state.topic,
                summaries=self.state.summaries,
                comparison=self.state.comparison,
                session_id=self.state.session_id,
            )
            self.state.report_path = report_path
            console.print(f"  [green]Report saved:[/green] {report_path}")
        elif step == "save_to_kb":
            raise NotImplementedError

    def _display_papers(self, papers):
        """Print a summary table of found papers."""
        table = Table(title=f"Papers Found ({len(papers)})")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", max_width=55)
        table.add_column("Year", width=6)
        table.add_column("Source", width=16)

        for i, p in enumerate(papers, 1):
            table.add_row(str(i), p.title, str(p.year), p.source)

        console.print(table)

    def _display_download_results(self, results):
        table = Table(title="PDF Download Results")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", max_width=55)
        table.add_column("Status", width=10)
        for i, r in enumerate(results, 1):
            status = "[green]✓ OK[/green]" if r.success else "[red]✗ Failed[/red]"
            table.add_row(str(i), r.title[:55], status)
        console.print(table)

    def _display_summaries(self, summaries):
        from rich.panel import Panel
        for s in summaries:
            content = (
                f"[bold]Problem:[/bold] {s.problem}\n\n"
                f"[bold]Method:[/bold] {s.method}\n\n"
                f"[bold]Datasets:[/bold] {', '.join(s.datasets) or 'N/A'}\n\n"
                f"[bold]Results:[/bold] {s.results}\n\n"
                f"[bold]Limitations:[/bold] {s.limitations}"
            )
            console.print(Panel(content, title=f"[cyan]{s.title[:70]}[/cyan]", expand=False))

    def _display_comparison(self, comparison: dict):
        if not comparison or "dimensions" in comparison == False:
            console.print("  [yellow]No comparison data to display[/yellow]")
            return

        dims = comparison.get("dimensions", {})
        for dim_name, dim_data in dims.items():
            desc = dim_data.get("description", "")
            console.print(f"  [bold cyan]{dim_name.capitalize()}:[/bold cyan] {desc}")

        gaps = comparison.get("research_gaps", [])
        if gaps:
            console.print("\n  [bold]Research Gaps:[/bold]")
            for gap in gaps:
                console.print(f"    • {gap}")

        directions = comparison.get("future_directions", [])
        if directions:
            console.print("\n  [bold]Future Directions:[/bold]")
            for d in directions:
                console.print(f"    • {d}")