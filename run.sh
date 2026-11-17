#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ! -f .venv/bin/activate ]]; then
    echo "Virtual environment not found. Complete the README installation steps first." >&2
    exit 1
fi

source .venv/bin/activate
exec python app.py
