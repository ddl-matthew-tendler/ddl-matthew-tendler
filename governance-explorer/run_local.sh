#!/usr/bin/env bash
set -euo pipefail
if [ -f .env ]; then export $(grep -v '^#' .env | xargs -d '\n'); fi
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
