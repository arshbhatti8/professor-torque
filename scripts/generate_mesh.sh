#!/usr/bin/env bash
# Run generate_mesh.py in the Hunyuan3D-2 environment (WSL).
# Example: scripts/generate_mesh.sh --front work/references/front.png --left work/references/left.png \
#          --back work/references/back.png --out work/ai_candidates/body --name body
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" && exec ~/tools/Hunyuan3D-2/.venv/bin/python scripts/generate_mesh.py "$@"
