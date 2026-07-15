"""First-Principles Crew: Skeptic -> Physicist -> Builder, sequential process.

Config (role/goal/backstory, task description/expected_output/agent/context)
lives in config/agents.yaml and config/tasks.yaml per CrewAI's standard
project layout: https://github.com/crewAIInc/crewAI#getting-started
"""

from crewai import Agent, Crew, LLM, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tasks.task_output import TaskOutput
from rich.console import Console
from rich.panel import Panel

from models import AssumptionSet, Fundamental, FundamentalSet, Recommendation

LLM_MODEL = LLM(
    model="ollama/llama3.2", base_url="http://localhost:11434", temperature=0.2
)

console = Console()


def _format_pydantic(obj) -> str | None:
    """Render a task's structured output as readable text instead of a repr/JSON dump."""
    if isinstance(obj, AssumptionSet):
        return "\n".join(
            f"{'[red]?[/red]' if a.questionable else '[green]OK[/green]'} {a.statement}\n"
            f"   [dim]{a.why}[/dim]"
            for a in obj.assumptions
        )
    if isinstance(obj, FundamentalSet):
        return "\n".join(f"• {f.truth}\n   [dim]{f.basis}[/dim]" for f in obj.fundamentals)
    if isinstance(obj, Fundamental):
        return f"{obj.truth}\n\n[dim]{obj.basis}[/dim]"
    if isinstance(obj, Recommendation):
        rests = "\n".join(f"  - {r}" for r in obj.rests_on)
        return f"{obj.recommendation}\n\nRests on:\n{rests}"
    return None


def print_task_output(output: TaskOutput) -> None:
    body = _format_pydantic(output.pydantic) if output.pydantic is not None else output.raw
    console.print(Panel(body, title=f"[bold]{output.agent}[/bold]"))


@CrewBase
class FirstPrinciplesCrew:
    """Skeptic -> Physicist -> Builder crew."""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def skeptic(self) -> Agent:
        return Agent(config=self.agents_config["skeptic"], llm=LLM_MODEL, verbose=False)

    @agent
    def physicist(self) -> Agent:
        return Agent(
            config=self.agents_config["physicist"], llm=LLM_MODEL, verbose=False
        )

    @agent
    def builder(self) -> Agent:
        return Agent(config=self.agents_config["builder"], llm=LLM_MODEL, verbose=False)

    @task
    def challenge_task(self) -> Task:
        return Task(
            config=self.tasks_config["challenge_task"], output_pydantic=AssumptionSet
        )

    @task
    def distill_task(self) -> Task:
        return Task(
            config=self.tasks_config["distill_task"], output_pydantic=FundamentalSet
        )

    @task
    def build_task(self) -> Task:
        return Task(
            config=self.tasks_config["build_task"], output_pydantic=Recommendation
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            task_callback=print_task_output,
        )
