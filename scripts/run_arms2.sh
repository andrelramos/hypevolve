#!/usr/bin/env bash
# Remaining arms: the two control arms + the two absolute-fitness GA arms.
# Sequential on purpose: benchmark timings must not overlap.
set -u
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
PY=.venv/bin/python

run () {  # run <config> <mode> <suffix> [extra...]
  echo "=================================================================="
  echo "[$(date +%H:%M:%S)] START $1 mode=$2 suffix=$3 ${4:-}"
  $PY -m hypevolve --config "$1" --mode "$2" --suffix="$3" ${4:-}
  echo "[$(date +%H:%M:%S)] END   $1 mode=$2 suffix=$3 rc=$?"
}

run experiments/configs/tornado_gso.yaml  sampling "-sampling"
run experiments/configs/pydantic_gso.yaml sampling "-sampling"
run experiments/configs/tornado_gso.yaml  ga       "-abs" "--fitness-mode absolute"
run experiments/configs/pydantic_gso.yaml ga       "-abs" "--fitness-mode absolute"
echo "[$(date +%H:%M:%S)] ALL ARMS DONE"
