from pathlib import Path

import pytest

from main import (
    build_smoke_command,
    discover_smoke_command,
    validate_bash_command,
    validate_edit_path,
)


def test_discovers_console_script(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'sample'\n[project.scripts]\nsample = 'sample:main'\n"
    )

    assert discover_smoke_command(tmp_path) == "sample --help"


def test_builds_import_smoke_from_project_name(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample-app'\n")

    assert build_smoke_command(discover_smoke_command(tmp_path)) == (
        "python -c \"import sample_app\""
    )


def test_rejects_outside_and_lockfile_edits(tmp_path: Path) -> None:
    assert validate_edit_path(tmp_path, "/etc/passwd") is not None
    assert validate_edit_path(tmp_path, str(tmp_path / "uv.lock")) is not None


def test_allows_uv_sync_and_rejects_git_commit(tmp_path: Path) -> None:
    assert validate_bash_command(tmp_path, "uv sync") is None
    assert validate_bash_command(tmp_path, "git commit -m fix") is not None


def test_invalid_smoke_override_is_rejected() -> None:
    with pytest.raises(ValueError):
        build_smoke_command("rm -rf .venv")
