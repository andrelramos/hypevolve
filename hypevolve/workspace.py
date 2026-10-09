"""Isolated per-individual workspace copies of the target project."""
import filecmp
import shutil
from pathlib import Path


class WorkspaceError(RuntimeError):
    pass


class WorkspaceManager:
    def __init__(self, root: Path, source: Path):
        self.root = Path(root)
        self.source = Path(source).resolve()
        if not self.source.is_dir():
            raise WorkspaceError(f"source not found: {self.source}")

    def _path_for(self, individual_id: int) -> Path:
        return self.root / f"indiv_{individual_id:04d}"

    def create(self, individual_id: int) -> str:
        dest = self._path_for(individual_id)
        if dest.exists():
            raise WorkspaceError(f"workspace exists: {dest}")
        self.root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.source, dest)
        return str(dest)

    def create_from(self, parent_workspace: str, individual_id: int) -> str:
        dest = self._path_for(individual_id)
        if dest.exists():
            raise WorkspaceError(f"workspace exists: {dest}")
        parent = Path(parent_workspace)
        if not parent.exists():
            raise WorkspaceError(f"parent workspace not found: {parent_workspace}")
        self.root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(parent, dest)
        return str(dest)

    def remove(self, individual_id: int) -> None:
        dest = self._path_for(individual_id)
        if dest.exists():
            shutil.rmtree(dest)

    def snapshot(self, individual_id: int, dest: Path) -> Path:
        src = self._path_for(individual_id)
        if not src.exists():
            raise WorkspaceError(f"no workspace for individual {individual_id}")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git"))
        return dest

    def integrity_check(self, individual_id: int, protected_files: list[str]) -> tuple[bool, list[str]]:
        """Check whether protected files differ from source workspace.

        Returns (ok, list_of_changed_files).
        """
        ws = self._path_for(individual_id)
        changed: list[str] = []
        for rel in protected_files:
            ws_file = ws / rel
            src_file = self.source / rel
            if not ws_file.exists():
                changed.append(rel)
                continue
            if not src_file.exists():
                continue
            if not filecmp.cmp(str(ws_file), str(src_file), shallow=False):
                changed.append(rel)
        return (len(changed) == 0, changed)
