#!/usr/bin/env bash
# Label the selected candidates again, assemble the character, and render a check sheet.
# Usage: scripts/rebuild.sh <version name>
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"; cd "$DIR"
V=${1:-v1}; O=work/ai_candidates/gateA; PY=~/tools/Hunyuan3D-2/.venv/bin/python
$PY scripts/label_mesh.py head $O/head_mvR_seed1.glb $O/head_mvR_input_front.png $O/head_mvR_input_left.png work/build/head_labelled.glb 2>&1 | grep WROTE
$PY scripts/label_mesh.py body $O/body_apose_seed1.glb $O/body_apose_input_front.png work/build/body_labelled.glb 2>&1 | grep WROTE
scripts/blender.sh --python scripts/build_character.py -- work/build/head_labelled.glb work/build/body_labelled.glb work/blend/torque_$V.blend 2>&1 | tr -d '\r' | grep -E 'PART .*EMPTY|SAVED|Error|Traceback' -A3 | cut -c1-200
scripts/blender.sh --python scripts/render_turnaround.py -- work/blend/torque_$V.blend work/build/r_$V 2>&1 | tr -d '\r' | grep -E 'STATS|Error|Traceback' -A3 | cut -c1-200
$PY -I - $V <<'PYEOF'
import sys
from PIL import Image
V = sys.argv[1]; R = f"work/build/r_{V}"
a = [Image.open(f"{R}/{v}.png").resize((400, 600)) for v in ("front", "three_quarter", "side", "back")]
b = [Image.open(f"{R}/{v}.png").resize((533, 533)) for v in ("head_front", "head_three_quarter", "head_side")]
s = Image.new("RGB", (1600, 1133), (40, 40, 40))
for i, im in enumerate(a): s.paste(im, (i * 400, 0))
for i, im in enumerate(b): s.paste(im, (i * 533, 600))
s.save(f"work/build/sheet_{V}.png")
PYEOF
