import json

from hypevolve.mcp import McpServer


def test_initialize_and_tools_list(tmp_path):
    server = McpServer(tmp_path / "results")
    initialized = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["name"] == "hypevolve"
    listed = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert listed is not None
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert {"start_evolution", "list_executions", "get_individual"} <= names


def test_tool_errors_are_mcp_results(tmp_path):
    server = McpServer(tmp_path / "results")
    response = server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                              "params": {"name": "get_execution", "arguments": {"session_id": "missing"}}})
    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "execution not found" in json.loads(result["content"][0]["text"])["error"]


def test_initialized_notification_has_no_response(tmp_path):
    assert McpServer(tmp_path / "results").handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_start_evolution_queues_a_session(monkeypatch, tmp_path):
    def finish_immediately(*_args, **_kwargs):
        return None

    monkeypatch.setattr("hypevolve.mcp.run_experiment", finish_immediately)
    server = McpServer(tmp_path / "results")
    target = tmp_path / "target"
    target.mkdir()
    result = server.call("start_evolution", {
        "target": str(target), "test_cmd": "true", "bench_cmd": "echo 1",
        "generations": 0, "max_hypotheses": 1, "harness": "codex",
        "name": "agent-run",
    })
    assert result == {"session_id": "agent-run", "status": "queued"}
    assert server.store.session("agent-run")["status"] == "queued"
