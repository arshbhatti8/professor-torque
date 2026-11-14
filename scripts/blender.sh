#!/usr/bin/env bash
# Run the project Blender from WSL without a window.
# Usage: scripts/blender.sh [file.blend] --python scripts/<name>.py -- [arguments]
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" && exec ./tools/blender/blender.exe -b "$@"
