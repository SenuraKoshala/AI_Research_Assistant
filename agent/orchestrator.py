import logging
from rich.console import Console
from agent.state import AgentState
from agent.planner import generate_plan

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
        """Dispatches to the correct tool. Each phase wires in a real implementation."""
        if step == "search_papers":
            raise NotImplementedError
        elif step == "download_pdfs":
            raise NotImplementedError
        elif step == "chunk_texts":
            raise NotImplementedError
        elif step == "summarize_papers":
            raise NotImplementedError
        elif step == "compare_papers":
            raise NotImplementedError
        elif step == "generate_report":
            raise NotImplementedError
        elif step == "save_to_kb":
            raise NotImplementedError