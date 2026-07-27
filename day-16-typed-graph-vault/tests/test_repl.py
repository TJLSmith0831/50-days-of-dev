from pathlib import Path

from src.repl import select_vault


def test_select_vault_prefers_private_vault(tmp_path: Path) -> None:
    (tmp_path / "example-vault").mkdir()
    (tmp_path / "vault").mkdir()

    assert select_vault(tmp_path) == tmp_path / "vault"


def test_select_vault_falls_back_to_example_vault(tmp_path: Path) -> None:
    (tmp_path / "example-vault").mkdir()

    assert select_vault(tmp_path) == tmp_path / "example-vault"
