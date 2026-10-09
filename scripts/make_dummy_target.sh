#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/targets/dummy"
rm -rf "$TARGET"
mkdir -p "$TARGET"
cat > "$TARGET/slow.py" <<'EOF'
def sum_squares(n: int) -> int:
    total = 0
    for i in range(n):
        total += i * i
    return total
EOF
cat > "$TARGET/test_slow.py" <<'EOF'
from slow import sum_squares

def test_correctness():
    assert sum_squares(3) == 5
    assert sum_squares(0) == 0
EOF
cat > "$TARGET/bench.py" <<'EOF'
import time
from slow import sum_squares

start = time.perf_counter()
for _ in range(50):
    sum_squares(20_000)
print(time.perf_counter() - start)
EOF
cd "$TARGET"
git init -q
git add -A
git -c user.email=hypevolve@local -c user.name=hypevolve commit -qm "dummy target"
echo "dummy target ready at $TARGET"
