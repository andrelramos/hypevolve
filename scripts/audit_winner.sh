#!/usr/bin/env bash
# Independent audit of a winning patch: run the target's FULL test suite, not just the gate.
set -u
WS="$1"; TARGET="$2"
HYPEVOLVE_ROOT="${HYPEVOLVE_ROOT:-$(git rev-parse --show-toplevel)}"
cd "$WS" || exit 2
case "$TARGET" in
  tornado)  "$HYPEVOLVE_ROOT/targets/.venv-tornado/bin/python" -m tornado.test.runtests 2>&1 | tail -6 ;;
  pydantic) "$HYPEVOLVE_ROOT/targets/.venv-pydantic/bin/python" -m pytest tests/ -q -x -o addopts='' -p no:cacheprovider 2>&1 | tail -6 ;;
esac
