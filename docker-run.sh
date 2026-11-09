#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SOPS_FILE="$HOME/.config/sops/secrets.enc.env"

# Ensure data directory has write permissions for non-root container user
mkdir -p data
chmod -R 777 data

if [ -f "$SOPS_FILE" ]; then
    echo "[*] Launching with SOPS secrets..."
    sops exec-env "$SOPS_FILE" "docker compose up -d --build"
else
    echo "[*] Launching Docker Compose..."
    docker compose up -d --build
fi

echo ""
echo "=========================================================="
echo "  🍳 Pantry Chef is running at: http://localhost:8501"
echo "=========================================================="
echo "  To view logs:    docker compose logs -f"
echo "  To stop:         docker compose down"
echo "=========================================================="
