import sys
from pathlib import Path

import pytest

from hypevolve.session_manager import (
    CmdAgentSession,
    FakeAgentSession,
    make_session,
)

PY = sys.executable


def test_fake_replays_replies_and_records_prompts(tmp_path):
    tp = tmp_path / "fake.log"
    s = FakeAgentSession("sid", str(tmp_path), ["first", "second"], transcript_path=tp)
    assert s.send("p1") == "first"
    assert s.send("p2") == "second"
    assert s.send("p3") == "second"  # last reply repeats
    assert s.sent == ["p1", "p2", "p3"]
    content = tp.read_text()
    assert "[PROMPT]" in content and "first" in content and "[RESPONSE]" in content


def test_cmd_echo_via_stdin(tmp_path):
    s = CmdAgentSession("ignored", "cat", "cat", str(tmp_path))
    assert s.send("hello agents") == "hello agents"


def test_cmd_extracts_json_result_field(tmp_path):
    script = f'{PY} -c "import json,sys; d=sys.stdin.read(); print(json.dumps({{{{\'result\': \'OK:\' + d}}}}))"'
    s = CmdAgentSession("sid", script, script, str(tmp_path))
    assert s.send("xyz") == "OK:xyz"


def test_cmd_nonzero_exit_raises(tmp_path):
    s = CmdAgentSession("sid", "false", "false", str(tmp_path))
    with pytest.raises(RuntimeError):
        s.send("boom")


def test_transcript_written(tmp_path):
    tp = tmp_path / "t.log"
    s = CmdAgentSession("sid", "cat", "cat", str(tmp_path), transcript_path=tp)
    s.send("abc")
    content = tp.read_text()
    assert "[PROMPT]" in content and "abc" in content and "[RESPONSE]" in content


def test_factory_builds_fake(tmp_path):
    cfg = {"kind": "fake", "replies": ["r1"]}
    s = make_session(cfg, "sid", str(tmp_path))
    assert isinstance(s, FakeAgentSession)


def test_factory_builds_cmd_with_templates(tmp_path):
    cfg = {
        "kind": "cmd",
        "start_cmd_template": "echo start-{session_id}",
        "cont_cmd_template": "echo cont-{session_id}",
    }
    s = make_session(cfg, "ABC123", str(tmp_path))
    assert isinstance(s, CmdAgentSession)
    assert s.send("hi") == "start-ABC123"
