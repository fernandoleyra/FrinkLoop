#!/bin/bash
# status.sh — Compatibility wrapper for the FrinkLoop CLI
ROOT_DIR="$(dirname "$(dirname "$0")")"
PYTHON_BIN="${PYTHON:-python3}"

cd "$ROOT_DIR"
"$PYTHON_BIN" frinkloop.py status "$@"
