"""Small, dependency-free MCP server for agent access to HypEvolve.

The server uses newline-delimited JSON-RPC over stdin/stdout, so it can be
registered directly as a local MCP command without running an HTTP service.
Execution data is still owned by :class:`ExecutionStore`.
"""
from __future__ import annotations

import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, cast

from .runtime import config_from_options, run_experiment
from .store import ExecutionStore

JsonObject = dict[str, object]
JsonValue = object


def _object(value: object, name: str = "arguments") -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return cast(JsonObject, value)


def _string(args: JsonObject, name: str, *, default: str | None = None) -> str:
    value = args.get(name, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _integer(args: JsonObject, name: str, *, minimum: int = 0) -> int:
    value = args.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _text_result(value: JsonValue, *, error: bool = False) -> JsonObject:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
        "structuredContent": value,
        **({"isError": True} if error else {}),
    }


class McpServer:
    """Handle the MCP subset needed by coding agents."""

    def __init__(self, results_root: str | Path = "results") -> None:
        self.store = ExecutionStore(results_root)
        self._locks: set[str] = set()
        self._lock = threading.Lock()

    @staticmethod
    def tools() -> list[JsonObject]:
        return [
            {
                "name": "start_evolution",
                "description": "Start an asynchronous HypEvolve optimization run on a local repository.",
                "inputSchema": {"type": "object", "required": ["target", "test_cmd", "bench_cmd", "generations", "max_hypotheses", "harness"], "properties": {
                    "target": {"type": "string", "description": "Repository folder to optimize."},
                    "test_cmd": {"type": "string", "description": "Command that exits 0 when the patch is correct."},
                    "bench_cmd": {"type": "string", "description": "Command whose last stdout line is duration in seconds."},
                    "generations": {"type": "integer", "minimum": 0},
                    "max_hypotheses": {"type": "integer", "minimum": 1},
                    "harness": {"type": "string", "enum": ["codex", "claude"]},
                    "initial_prompt": {"type": "string"}, "model": {"type": "string"},
                    "population_size": {"type": "integer", "minimum": 1}, "name": {"type": "string"},
                }},
            },
            {"name": "list_executions", "description": "List HypEvolve executions and their current status.", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "get_execution", "description": "Get a complete execution summary and artifacts.", "inputSchema": {"type": "object", "required": ["session_id"], "properties": {"session_id": {"type": "string"}}}},
            {"name": "get_generations", "description": "Get the measured generation timeline for an execution.", "inputSchema": {"type": "object", "required": ["session_id"], "properties": {"session_id": {"type": "string"}}}},
            {"name": "get_individual", "description": "Inspect an agent prompt, response, hypothesis, tests, and fitness.", "inputSchema": {"type": "object", "required": ["session_id", "individual_id"], "properties": {"session_id": {"type": "string"}, "individual_id": {"type": "integer"}}}},
            {"name": "list_hypotheses", "description": "List active hypotheses for an execution.", "inputSchema": {"type": "object", "required": ["session_id"], "properties": {"session_id": {"type": "string"}}}},
            {"name": "add_hypothesis", "description": "Add a hypothesis for the next evolution step.", "inputSchema": {"type": "object", "required": ["session_id", "text"], "properties": {"session_id": {"type": "string"}, "text": {"type": "string"}}}},
        ]

    def _start(self, args: JsonObject) -> JsonObject:
        target = _string(args, "target")
        test_cmd = _string(args, "test_cmd")
        bench_cmd = _string(args, "bench_cmd")
        generations = _integer(args, "generations")
        max_hypotheses = _integer(args, "max_hypotheses", minimum=1)
        harness = _string(args, "harness")
        if harness not in {"codex", "claude"}:
            raise ValueError("harness must be 'codex' or 'claude'")
        name = args.get("name")
        session_id = (name if isinstance(name, str) and name.strip() else datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ"))
        model = args.get("model")
        initial_prompt = args.get("initial_prompt", "")
        population_size = args.get("population_size", 4)
        if model is not None and not isinstance(model, str):
            raise ValueError("model must be a string")
        if not isinstance(initial_prompt, str):
            raise ValueError("initial_prompt must be a string")
        if isinstance(population_size, bool) or not isinstance(population_size, int) or population_size < 1:
            raise ValueError("population_size must be an integer >= 1")
        cfg = config_from_options(name=session_id, source_path=target, test_cmd=test_cmd,
            bench_cmd=bench_cmd, harness=harness, model=model, generations=generations,
            max_hypotheses=max_hypotheses, initial_prompt=initial_prompt,
            population_size=population_size)
        with self._lock:
            if session_id in self._locks:
                raise ValueError(f"execution already running: {session_id}")
            self.store.create_session(session_id, {"name": session_id, "source_path": cfg.source_path,
                "config": {"target": target, "test_cmd": test_cmd, "bench_cmd": bench_cmd,
                            "generations": generations, "max_hypotheses": max_hypotheses,
                            "harness": harness}})
            self._locks.add(session_id)

        def execute() -> None:
            try:
                run_experiment(cfg, self.store.root / session_id, self.store)
            finally:
                with self._lock:
                    self._locks.discard(session_id)

        threading.Thread(target=execute, name=f"hypevolve-{session_id}", daemon=False).start()
        return {"session_id": session_id, "status": "queued"}

    def call(self, name: str, arguments: object) -> JsonValue:
        args = _object(arguments)
        actions: dict[str, Callable[[], JsonValue]] = {
            "start_evolution": lambda: self._start(args),
            "list_executions": lambda: self.store.list_sessions(),
            "get_execution": lambda: self.store.session(_string(args, "session_id")),
            "get_generations": lambda: self.store.generations(_string(args, "session_id")),
            "get_individual": lambda: self.store.individual(_string(args, "session_id"), _integer(args, "individual_id")),
            "list_hypotheses": lambda: self.store.hypotheses(_string(args, "session_id")),
            "add_hypothesis": lambda: self.store.add_hypothesis(_string(args, "session_id"), _string(args, "text")),
        }
        if name not in actions:
            raise ValueError(f"unknown tool: {name}")
        return actions[name]()

    def handle(self, message: object) -> JsonObject | None:
        request = _object(message, "request")
        method = request.get("method")
        request_id = request.get("id")
        if not isinstance(method, str):
            raise ValueError("request method must be a string")
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "hypevolve", "version": "0.1.0"},
            }}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tools()}}
        if method == "tools/call":
            params = _object(request.get("params"), "params")
            name = _string(params, "name")
            try:
                result = _text_result(self.call(name, params.get("arguments", {})))
            except (KeyError, TypeError, ValueError, OSError, RuntimeError) as exc:
                result = _text_result({"error": str(exc)}, error=True)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        raise ValueError(f"unsupported method: {method}")


def serve_stdio(results_root: str | Path = "results") -> None:
    """Run the MCP JSON-RPC loop; stdout is reserved for protocol messages."""
    server = McpServer(results_root)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = server.handle(json.loads(line))
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None,
                              "error": {"code": -32600, "message": str(exc)}}, ensure_ascii=False), flush=True)
