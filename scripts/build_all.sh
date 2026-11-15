#!/usr/bin/env bash
# Build the rigged Professor Torque model from the painted AI meshes, then run the range-of-motion check.
# All corrections (texture cleanup, collar, cuffs, tie, hands, tailoring, eyes, mouth, weights) are in these steps,
# so each rebuild gives the same corrected model.
# Usage: scripts/build_all.sh [--no-check]   (inputs: work/v4/head_hi1_cm.glb, work/v3/body_f_cm.glb, work/v4/base_hand.blend)
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"; cd "$DIR"
PY=~/tools/Hunyuan3D-2/.venv/bin/python
run() { scripts/blender.sh "$@" 2>&1 | tr -d '\r' | grep -E '^(CHECK)|Error|Traceback' -A6 | cut -c1-220 || true; }
echo "1/7 texture cleanup";  $PY scripts/clean_texture.py work/v3/body_f_cm.glb work/v4/body_clean.glb --shirt_tex work/v4/body_shirt_tex.png | grep -E 'WROTE' || true
echo "2/7 head and body";    run --python scripts/v3_assemble.py -- work/v4/head_hi1_cm.glb work/v4/body_clean.glb work/blend/torque_a.blend --head_scale=1.12 --head_dz=0.03 --cut_z=1.535 --collar_r=0.084 --back=1.05
echo "3/7 parts";            run work/blend/torque_a.blend --python scripts/v4_parts.py -- work/v4/base_hand.blend work/blend/torque_b.blend work/v4/body_shirt_tex.png
echo "4/7 tailoring";        run work/blend/torque_b.blend --python scripts/v7_tailor.py -- work/blend/torque_tailored.blend
echo "5/7 eyes and mouth";   run work/blend/torque_tailored.blend --python scripts/v5_face.py -- work/blend/torque_face.blend
echo "6/7 rig";              run work/blend/torque_face.blend --python scripts/v4_rig.py -- work/blend/torque_rigged.blend
if [ "${1:-}" != "--no-check" ]; then
  echo "7/7 range-of-motion check (pictures in work/pose_check)"
  scripts/blender.sh work/blend/torque_rigged.blend --python scripts/v6_pose_check.py -- --sheet=work/pose_check 2>&1 | tr -d '\r' | grep -E '^CHECK|Error|Traceback' -A6 || true
fi
echo "Result: work/blend/torque_rigged.blend"
