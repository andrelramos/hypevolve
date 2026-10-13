#!/bin/bash
# Builds the HypEvolve explainer in every site language with headless Chrome + ffmpeg.
#   ./video/render.sh            -> QC stills + videos for pt en es zh ja
#   ./video/render.sh qc         -> QC stills only (fast review)
#   ./video/render.sh qc en      -> QC stills for one language
#   ./video/render.sh all en     -> stills + video for one language
# Outputs: docs/media/hypevolve-<lang>.mp4 and docs/media/hypevolve-<lang>.jpg (poster).
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-all}"
LANGS="${2:-pt en es zh ja}"
OUT=../docs/media
QC_TIMES=3.3,6,11.2,14.3,17,21.5,26.7,31,35.1,39,44,48,54,58,61.9,65.9,72.8,78,83,86.9

python3 -c "import websocket" 2>/dev/null || python3 -m pip install --user websocket-client
mkdir -p build "$OUT"
if [ "$MODE" != "qc" ]; then
  if python3 -c "import numpy" 2>/dev/null; then python3 music.py build/bgm.wav; else uv run --with numpy python music.py build/bgm.wav; fi
fi
for lang in $LANGS; do
  rm -rf "qc/$lang" && mkdir -p "qc/$lang"
  python3 render.py index.html "$lang" stills "qc/$lang" "$QC_TIMES"
  echo "QC -> $(pwd)/qc/$lang"
  [ "$MODE" = "qc" ] && continue
  python3 render.py index.html "$lang" video "build/silent-$lang.mp4" 30
  ffmpeg -y -loglevel error -i "build/silent-$lang.mp4" -i build/bgm.wav -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart "$OUT/hypevolve-$lang.mp4"
  ffmpeg -y -loglevel error -ss 86.6 -i "$OUT/hypevolve-$lang.mp4" -frames:v 1 -vf scale=1280:-2 -q:v 3 "$OUT/hypevolve-$lang.jpg"
  echo "OK -> $OUT/hypevolve-$lang.mp4"
done
