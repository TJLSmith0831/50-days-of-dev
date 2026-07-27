from pathlib import Path

import pytest

from src.vault import VaultValidationError, load_vault


def test_load_vault_builds_nodes_and_typed_edges(tmp_path: Path) -> None:
    (tmp_path / "graph.yaml").write_text(
        "relations:\n  decided_by: governed by a decision record\n"
    )
    (tmp_path / "job-queue.md").write_text(
        "---\nid: job-queue\nkind: component\nlinks:\n  - relation: decided_by\n"
        "    target: adr-007\n---\n\nThe service that runs background jobs.\n"
    )
    (tmp_path / "adr-007.md").write_text(
        "---\nid: adr-007\nkind: decision\nlinks: []\n---\n\nUse Postgres for jobs.\n"
    )

    graph = load_vault(tmp_path)

    assert graph.nodes["job-queue"].kind == "component"
    assert graph.nodes["job-queue"].body == "The service that runs background jobs."
    assert graph.edges[0].source == "job-queue"
    assert graph.edges[0].relation == "decided_by"
    assert graph.edges[0].target == "adr-007"


def test_load_vault_reads_relation_descriptions(tmp_path: Path) -> None:
    (tmp_path / "graph.yaml").write_text(
        "relations:\n  decided_by: governed by a decision record\n"
    )
    (tmp_path / "note.md").write_text(
        "---\nid: note\nkind: component\nlinks: []\n---\n\nA note.\n"
    )

    graph = load_vault(tmp_path)

    assert graph.relations["decided_by"] == "governed by a decision record"


@pytest.mark.parametrize(
    ("notes", "expected_message"),
    [
        (
            [
                "---\nid: job-queue\nkind: component\nlinks: []\n---\n",
                "---\nid: job-queue\nkind: decision\nlinks: []\n---\n",
            ],
            "duplicate node id: job-queue",
        ),
        (
            [
                "---\nid: job-queue\nkind: component\nlinks:\n  - relation: replaces\n"
                "    target: adr-007\n---\n",
                "---\nid: adr-007\nkind: decision\nlinks: []\n---\n",
            ],
            "unknown relation: replaces",
        ),
        (
            [
                "---\nid: job-queue\nkind: component\nlinks:\n  - relation: decided_by\n"
                "    target: missing-note\n---\n",
            ],
            "unknown link target: missing-note",
        ),
        (["not frontmatter"], "invalid frontmatter"),
    ],
)
def test_load_vault_collects_validation_errors(
    tmp_path: Path, notes: list[str], expected_message: str
) -> None:
    (tmp_path / "graph.yaml").write_text(
        "relations:\n  decided_by: governed by a decision record\n"
    )
    for index, note in enumerate(notes):
        (tmp_path / f"note-{index}.md").write_text(note)

    with pytest.raises(VaultValidationError) as error:
        load_vault(tmp_path)

    assert expected_message in error.value.messages
