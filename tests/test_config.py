from pathlib import Path

import pytest

from hypevolve.config import ExperimentConfig

FULL = """
name: exp1
source_path: targets/dummy
test_cmd: "python3 -m pytest -q"
bench_cmd: "python3 bench.py"
agent_name: claude
agents:
  claude:
    kind: cmd
    start_cmd_template: "claude -p --session-id {session_id}"
    cont_cmd_template: "claude -p --resume {session_id}"
""".strip()


def write(tmp_path: Path, text: str) -> str:
    p = tmp_path / "cfg.yaml"
    p.write_text(text)
    return str(p)


def test_load_full_config_with_defaults(tmp_path):
    cfg = ExperimentConfig.load(write(tmp_path, FULL))
    assert cfg.name == "exp1"
    assert cfg.generations == 12
    assert cfg.population_size == 8
    assert cfg.agents["claude"]["kind"] == "cmd"
    assert cfg.alpha == 0.05


def test_missing_required_keys_reported_together(tmp_path):
    with pytest.raises(ValueError) as exc:
        ExperimentConfig.load(write(tmp_path, "name: only-name\n"))
    msg = str(exc.value)
    assert "source_path" in msg
    assert "bench_cmd" in msg
    assert "agents" in msg


def test_unknown_agent_name_rejected(tmp_path):
    bad = FULL.replace("agent_name: claude", "agent_name: gpt")
    with pytest.raises(ValueError):
        ExperimentConfig.load(write(tmp_path, bad))
