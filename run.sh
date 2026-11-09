#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "[!] Virtual environment not found. Please set up .venv first."
    exit 1
fi

source .venv/bin/activate
echo "[*] Launching Pantry Chef on http://localhost:8501 ..."
streamlit run app.py
