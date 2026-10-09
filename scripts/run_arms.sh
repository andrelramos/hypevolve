#!/usr/bin/env bash
# Runs the four experiment arms SEQUENTIALLY: benchmark timings must not overlap.
set -u
cd /Users/andreramos/Dev/algoritmos-geneticos-com-llm
PY=.venv/bin/python

run () {  # run <config> <mode> <suffix>
  echo "=================================================================="
  echo "[$(date +%H:%M:%S)] START $1 mode=$2 suffix=$3"
  $PY -m hypevolve --config "$1" --mode "$2" --suffix "$3"
  echo "[$(date +%H:%M:%S)] END   $1 mode=$2 rc=$?"
}

run experiments/configs/tornado_gso.yaml  ga       ""
run experiments/configs/tornado_gso.yaml  sampling "-sampling"
run experiments/configs/pydantic_gso.yaml ga       ""
run experiments/configs/pydantic_gso.yaml sampling "-sampling"
echo "[$(date +%H:%M:%S)] ALL ARMS DONE"
