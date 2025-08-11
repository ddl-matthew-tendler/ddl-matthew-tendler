#!/usr/bin/env bash
set -euo pipefail

# Root of the repo no matter where this script is called from
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$REPO_DIR/governance-explorer"

echo "[Governance Explorer] Using Python: $(which python) ($(python --version))"
echo "[Governance Explorer] Working dir: $APP_DIR"

# Make sure deps are present (safe to re-run; Domino will cache wheels)
pip install --user -r "$APP_DIR/requirements.txt"

# Run the app — app.py will pick DOMINO_APP_PORT automatically,
# and default to 8888 when the env var is missing.
python "$APP_DIR/src/app.py"