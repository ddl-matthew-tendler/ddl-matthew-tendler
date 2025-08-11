#!/usr/bin/env bash
set -euo pipefail
streamlit run src/app.py --server.port="${DOMINO_APP_PORT:-8888}" --server.address=0.0.0.0
