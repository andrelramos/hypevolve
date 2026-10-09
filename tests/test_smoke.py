"""End-to-end smoke test: dummy target + echo (cat) agent, full pipeline offline."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "smoke"
CONFIG_TEMPLATE = ROOT / "experiments" / "configs" / "smoke.template.yaml"
TARGET_SCRIPT = ROOT / "scripts" / "make_dummy_target.sh"


@pytest.mark.slow
def test_smoke_end_to_end():
    """Run the full hypevolve pipeline on a dummy target with cat agent."""
    # Clean previous artifacts
    if RESULTS.exists():
        shutil.rmtree(RESULTS)

    # 1. Prepare dummy target
    subprocess.run([str(TARGET_SCRIPT)], cwd=str(ROOT), check=True)

    # 2. Generate machine-specific config
    configs_dir = ROOT / "experiments" / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    py_path = subprocess.check_output(
        ["which", "python3"], text=True, cwd=str(ROOT)
    ).strip()
    template = CONFIG_TEMPLATE.read_text()
    (configs_dir / "smoke.yaml").write_text(template.replace("{PY}", py_path))

    # 3. Run hypevolve
    result = subprocess.run(
        ["python3", "-m", "hypevolve", "--config", str(configs_dir / "smoke.yaml")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"hypevolve failed:\n{result.stderr}"

    # 4. Verify artifacts
    assert RESULTS.exists(), "results/smoke/ directory not created"
    assert (RESULTS / "summary.json").exists(), "summary.json missing"
    assert (RESULTS / "hypotheses.json").exists(), "hypotheses.json missing"
    assert (RESULTS / "best").exists(), "best/ snapshot missing"
    assert (RESULTS / "transcripts").exists(), "transcripts/ missing"

    # 5. Validate summary structure
    summary = json.loads((RESULTS / "summary.json").read_text())
    assert len(summary["generations"]) == 3, "Expected gen 0 + 2 evolution gens"
    assert summary["best_fitness"] >= 1.0

    # 6. Validate hypotheses were extracted from echo replies
    hypotheses = json.loads((RESULTS / "hypotheses.json").read_text())
    assert hypotheses, "No hypotheses extracted from echo replies"
    assert all(h["status"] != "proposed" for h in hypotheses)
