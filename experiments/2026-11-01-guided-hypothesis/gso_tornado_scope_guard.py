"""Reject Tornado GSO candidates that modify files outside the shared edit scope."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

IGNORED_DIRECTORIES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "build",
    "dist",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
IGNORED_NAMES = {".coverage"}
ALLOWED_PATH = Path("tornado/concurrent.py")


def _files(root: Path) -> dict[Path, str]:
    """Return hashes of persistent files, excluding interpreter/test caches."""
    result: dict[Path, str] = {}
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in IGNORED_DIRECTORIES)
        current_path = Path(current)
        for name in sorted(filenames):
            path = current_path / name
            if name in IGNORED_NAMES or path.suffix in IGNORED_SUFFIXES:
                continue
            relative = path.relative_to(root)
            if path.is_symlink():
                content = os.readlink(path).encode("utf-8")
            else:
                content = path.read_bytes()
            result[relative] = hashlib.sha256(content).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()

    candidate = args.candidate.resolve()
    baseline = args.baseline.resolve()
    if not candidate.is_dir() or not baseline.is_dir():
        print("scope guard: candidate and baseline must be directories", file=sys.stderr)
        return 2

    candidate_files = _files(candidate)
    baseline_files = _files(baseline)
    paths = set(candidate_files) | set(baseline_files)
    changed = sorted(
        path for path in paths if candidate_files.get(path) != baseline_files.get(path)
    )
    unauthorized = [path for path in changed if path != ALLOWED_PATH]
    if unauthorized:
        print(
            "scope guard: changes outside tornado/concurrent.py: "
            + ", ".join(path.as_posix() for path in unauthorized),
            file=sys.stderr,
        )
        return 1
    if not (candidate / ALLOWED_PATH).is_file():
        print("scope guard: tornado/concurrent.py is missing", file=sys.stderr)
        return 1
    print("scope guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
