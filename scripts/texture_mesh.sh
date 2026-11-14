#!/usr/bin/env bash
# Run texture_mesh.py in the Hunyuan3D-2 environment (WSL).
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" && exec ~/tools/Hunyuan3D-2/.venv/bin/python scripts/texture_mesh.py "$@"
