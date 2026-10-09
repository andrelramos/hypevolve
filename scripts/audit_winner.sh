#!/usr/bin/env bash
# Independent audit of a winning patch: run the target's FULL test suite, not just the gate.
set -u
WS="$1"; TARGET="$2"
cd "$WS" || exit 2
case "$TARGET" in
  tornado)  /Users/andreramos/Dev/algoritmos-geneticos-com-llm/targets/.venv-tornado/bin/python -m tornado.test.runtests 2>&1 | tail -6 ;;
  pydantic) /Users/andreramos/Dev/algoritmos-geneticos-com-llm/targets/.venv-pydantic/bin/python -m pytest tests/ -q -x -o addopts='' -p no:cacheprovider 2>&1 | tail -6 ;;
esac
