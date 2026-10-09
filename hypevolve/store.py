"""Filesystem-backed read/write model for HypEvolve execution artifacts.

The engine deliberately writes portable JSON artifacts.  This store makes those
artifacts a stable API boundary for the CLI and the web server; no database is
required beside a project being optimized.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

import icontract

from .contracts import SessionStatus, has_hypothesis_text, is_valid_session_transition


class SessionData(TypedDict, total=False):
    id: str
    status: SessionStatus
    name: str
    source_path: str
    created_at: str
    updated_at: str
    started_at: str
    completed_at: str
    error: str


def _valid_session_id(session_id: str) -> bool:
    return bool(session_id) and Path(session_id).name == session_id and session_id not in {".", ".."}


class ExecutionStore:
    def __init__(self, results_root: str | Path = "results") -> None:
        self.root = Path(results_root).resolve()

    def _dir(self, session_id: str) -> Path:
        path = (self.root / session_id).resolve()
        if path.parent != self.root or not path.is_dir():
            raise KeyError(f"execution not found: {session_id}")
        return path

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()

    @icontract.require(lambda session_id: _valid_session_id(session_id), "session id must be a single path component")
    @icontract.require(lambda data: "status" not in data, "initial status is owned by the store")
    def create_session(self, session_id: str, data: dict[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / session_id
        path.mkdir(parents=False, exist_ok=False)
        payload = {"id": session_id, "status": "queued", "created_at": self.now(), **data}
        (path / "session.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @icontract.require(lambda session_id: _valid_session_id(session_id), "session id must be a single path component")
    @icontract.require(lambda changes: "status" in changes, "every update declares the intended state")
    @icontract.require(lambda changes: changes.get("status") in {"queued", "running", "completed", "failed"}, "invalid session state")
    def update_session(self, session_id: str, **changes: Any) -> dict[str, Any]:
        path = self._dir(session_id) / "session.json"
        data = cast(dict[str, Any], self._read(path, {"id": session_id}))
        previous = cast(SessionStatus | None, data.get("status"))
        next_status = cast(SessionStatus, changes["status"])
        if not is_valid_session_transition(previous, next_status):
            raise ValueError(f"terminal session cannot return to running: {session_id}")
        data.update(changes)
        data["updated_at"] = self.now()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def list_sessions(self) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        sessions = []
        for path in self.root.iterdir():
            if not path.is_dir():
                continue
            data = self._read(path / "session.json", None)
            if data is None and (path / "run_log.json").exists():
                log = self._read(path / "run_log.json", {})
                data = {"id": path.name, "status": "completed", "name": path.name,
                        "generations": log.get("generations", 0), "source_path": ""}
            if data:
                log = self._read(path / "run_log.json", {})
                data["individual_count"] = len(log.get("individuals", []))
                data["completed_generations"] = self._read(path / "checkpoint.json", {}).get("through_generation")
                sessions.append(data)
        return sorted(sessions, key=lambda item: item.get("created_at", ""), reverse=True)

    def session(self, session_id: str) -> dict[str, Any]:
        path = self._dir(session_id)
        data = self._read(path / "session.json", {"id": session_id, "status": "unknown"})
        log = self._read(path / "run_log.json", self._read(path / "checkpoint.json", {}))
        data["run"] = log
        data["generations_data"] = self.generations(session_id)
        return data

    def generations(self, session_id: str) -> list[dict[str, Any]]:
        path = self._dir(session_id)
        log = self._read(path / "run_log.json", self._read(path / "checkpoint.json", {}))
        grouped: dict[int, list[dict[str, Any]]] = {}
        for item in log.get("individuals", []):
            grouped.setdefault(int(item["generation"]), []).append(item)
        return [
            {"generation": generation, "individuals": values,
             "best_fitness": max((v.get("fitness", 0) for v in values), default=0),
             "mean_fitness": sum(v.get("fitness", 0) for v in values) / len(values) if values else 0}
            for generation, values in sorted(grouped.items())
        ]

    def individual(self, session_id: str, individual_id: int) -> dict[str, Any]:
        path = self._dir(session_id)
        log = self._read(path / "run_log.json", self._read(path / "checkpoint.json", {}))
        for item in log.get("individuals", []):
            if item.get("individual_id") == individual_id:
                return item
        raise KeyError(f"individual not found: {individual_id}")

    def hypotheses(self, session_id: str) -> list[dict[str, Any]]:
        path = self._dir(session_id)
        data = self._read(path / "hypotheses.json", [])
        return [h for h in data if not h.get("deleted")]

    def _write_hypotheses(self, session_id: str, data: list[dict[str, Any]]) -> None:
        (self._dir(session_id) / "hypotheses.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    @icontract.require(lambda text: has_hypothesis_text(text), "hypothesis must not be blank")
    def add_hypothesis(self, session_id: str, text: str, generation: int = -1) -> dict[str, Any]:
        data = self.hypotheses(session_id)
        # Manual IDs deliberately live in a separate namespace from h1, h2… generated
        # by HypothesisTracker while an execution is still running.
        item = {"id": f"manual-{int(datetime.now(UTC).timestamp() * 1_000_000)}", "text": text, "generation": generation,
                "individual_id": -1, "status": "proposed", "manual": True}
        data.append(item)
        self._write_hypotheses(session_id, data)
        return item

    @icontract.require(lambda text: has_hypothesis_text(text), "hypothesis must not be blank")
    def update_hypothesis(self, session_id: str, hypothesis_id: str, text: str) -> dict[str, Any]:
        data = self.hypotheses(session_id)
        for item in data:
            if item.get("id") == hypothesis_id:
                item["text"] = text
                item["edited_at"] = self.now()
                self._write_hypotheses(session_id, data)
                return item
        raise KeyError(f"hypothesis not found: {hypothesis_id}")

    def delete_hypothesis(self, session_id: str, hypothesis_id: str) -> None:
        data = self.hypotheses(session_id)
        kept = [item for item in data if item.get("id") != hypothesis_id]
        if len(kept) == len(data):
            raise KeyError(f"hypothesis not found: {hypothesis_id}")
        self._write_hypotheses(session_id, kept)
