"""Launch the arm driver in its own session so a harness kill doesn't take it down."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
log = ROOT / "results/run_arms.log"
log.parent.mkdir(parents=True, exist_ok=True)
fh = open(log, "ab", buffering=0)
proc = subprocess.Popen(
    ["./scripts/run_arms3.sh"],
    cwd=ROOT,
    stdout=fh,
    stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,
    start_new_session=True,
)
print(f"pid={proc.pid} log={log}")
