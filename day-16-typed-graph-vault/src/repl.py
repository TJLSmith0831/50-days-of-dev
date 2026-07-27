from pathlib import Path
import webbrowser

import ollama

from src.llm import plan_question, synthesize_answer
from src.renderer import render_graph
from src.traversal import TraversalResult, traverse
from src.vault import VaultValidationError, load_vault


def select_vault(project_root: Path) -> Path:
    private_vault = project_root / "vault"
    if private_vault.is_dir():
        return private_vault
    example_vault = project_root / "example-vault"
    if example_vault.is_dir():
        return example_vault
    raise FileNotFoundError("Create vault/ or provide example-vault/ before starting the REPL.")


class ReplApp:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.vault_path = select_vault(project_root)
        self.graph = load_vault(self.vault_path)
        self.client = ollama.Client()
        self.latest: TraversalResult | None = None

    def reload(self) -> str:
        try:
            graph = load_vault(self.vault_path)
        except VaultValidationError as error:
            return "Reload failed:\n" + "\n".join(error.messages)
        self.graph = graph
        return f"Reloaded {len(graph.nodes)} notes."

    def ask(self, question: str) -> str:
        plan = plan_question(self.client, question, self.graph)
        if plan is None:
            return "No grounded graph path found."
        result = traverse(self.graph, plan)
        if not result.path:
            return "No grounded graph path found."
        self.latest = result
        answer = synthesize_answer(self.client, question, result)
        path = " -> ".join(node.id for node in result.nodes)
        return f"{answer}\n\nPath: {path}"

    def show(self, node_id: str) -> str:
        node = self.graph.nodes.get(node_id)
        if node is None:
            return f"Unknown node: {node_id}"
        links = "\n".join(f"- {link.relation} -> {link.target}" for link in node.links) or "- none"
        return f"{node.id} ({node.kind})\n{node.body}\nLinks:\n{links}"

    def graph_file(self) -> Path:
        output = render_graph(self.graph, self.latest.path if self.latest else [], self.project_root / "graph.html")
        webbrowser.open(output.as_uri())
        return output

    def run(self) -> None:
        print(f"Loaded {len(self.graph.nodes)} notes from {self.vault_path.name}. Type help for commands.")
        while True:
            try:
                command = input("graph> ").strip()
            except EOFError:
                return
            if command in {"quit", "exit"}:
                return
            if command == "help":
                print("ask <question> | show <node-id> | graph | reload | quit")
            elif command.startswith("ask "):
                print(self.ask(command[4:]))
            elif command.startswith("show "):
                print(self.show(command[5:]))
            elif command == "graph":
                print(f"Wrote {self.graph_file()}")
            elif command == "reload":
                print(self.reload())
            elif command:
                print("Unknown command. Type help for commands.")
