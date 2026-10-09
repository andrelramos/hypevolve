#!/usr/bin/env bash
# Wait for the usage window to reopen tonight, then finish the pydantic arms and
# rebuild analysis + report. Sequential on purpose: two arms benchmarking at once
# would contaminate both timings.
set -u
cd /Users/andreramos/Dev/algoritmos-geneticos-com-llm
PY=.venv/bin/python
LOG=results/run_arms.log
AT="${1:-21:00}"

say () { echo "[$(date +%H:%M:%S)] [tonight] $*" >> "$LOG"; }

now=$(date +%s)
tgt=$(date -j -f "%Y-%m-%d %H:%M" "$(date +%F) $AT" +%s)
[ "$tgt" -le "$now" ] && tgt=$((tgt + 86400))
say "armed for $(date -j -f %s "$tgt" '+%F %H:%M') ($(((tgt - now) / 60)) min from now)"
sleep $((tgt - now))

say "window open — archiving the interrupted partial arm"
if [ -d results/pydantic-c2647ab ] && [ ! -f results/pydantic-c2647ab/run_log.json ]; then
  mkdir -p results/_discarded
  mv results/pydantic-c2647ab "results/_discarded/pydantic-c2647ab-nofinalmsg-$(date +%m%d-%H%M)"
fi

say "running pydantic arms (repair_arms.py)"
$PY scripts/repair_arms.py
say "rebuilding analysis bundle"
$PY scripts/analyze_arms.py >> "$LOG" 2>&1
say "rebuilding report"
$PY scripts/build_report.py >> "$LOG" 2>&1
say "TONIGHT DONE"
