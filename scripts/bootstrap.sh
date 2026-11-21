#!/usr/bin/env bash
# Create a local virtualenv and install the lab package. Does not contact Okta.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -e ".[dev]"
if [[ ! -f .env ]]; then
  cp .env.example .env
fi
echo "Installed. Next: make demo"
