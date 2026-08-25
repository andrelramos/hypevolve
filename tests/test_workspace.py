import subprocess
from pathlib import Path

import pytest

from hypevolve.workspace import WorkspaceManager


@pytest.fixture
def source_repo(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1\n")
    subprocess.run(["git", "init", "-q"], cwd=src, check=True)
    return src


def test_create_copies_source_including_git(tmp_path, source_repo):
    wm = WorkspaceManager(tmp_path / "ws", source_repo)
    ws = Path(wm.create(0))
    assert (ws / "app.py").read_text() == "x = 1\n"
    assert (ws / ".git").exists()


def test_create_from_inherits_parent_changes(tmp_path, source_repo):
    wm = WorkspaceManager(tmp_path / "ws", source_repo)
    parent = wm.create(0)
    Path(parent, "app.py").write_text("x = 2\n")
    child = Path(wm.create_from(parent, 1))
    assert child.joinpath("app.py").read_text() == "x = 2\n"


def test_remove_deletes_tree(tmp_path, source_repo):
    wm = WorkspaceManager(tmp_path / "ws", source_repo)
    ws = wm.create(3)
    wm.remove(3)
    assert not Path(ws).exists()


def test_snapshot_copies_to_dest_without_git(tmp_path, source_repo):
    wm = WorkspaceManager(tmp_path / "ws", source_repo)
    wm.create(0)
    dest = tmp_path / "snap"
    out = wm.snapshot(0, dest)
    assert Path(out).joinpath("app.py").exists()
    assert not Path(out).joinpath(".git").exists()
