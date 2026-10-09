"""Wait for the running arm driver to exit, then re-run the pydantic GA arm.

Sequential on purpose: two arms benchmarking at once would contaminate both timings.
"""
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "results/run_arms.log"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def main() -> None:
    pids = [
        int(p)
        for p in subprocess.run(
            ["pgrep", "-f", "run_arms3"], capture_output=True, text=True
        ).stdout.split()
    ]
    with open(LOG, "a") as fh:
        fh.write(f"[queue] waiting for driver pids {pids}\n")
    while any(alive(p) for p in pids):
        time.sleep(20)
    with open(LOG, "a") as fh:
        fh.write(f"[{time.strftime('%H:%M:%S')}] START pydantic ga (requeued)\n")
        fh.flush()
        rc = subprocess.run(
            [".venv/bin/python", "-m", "hypevolve", "--config",
             "experiments/configs/pydantic_gso.yaml", "--mode", "ga", "--suffix="],
            cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT,
        ).returncode
        fh.write(f"[{time.strftime('%H:%M:%S')}] END pydantic ga rc={rc}\n")
        fh.write("[queue] ALL ARMS DONE\n")


if __name__ == "__main__":
    main()
