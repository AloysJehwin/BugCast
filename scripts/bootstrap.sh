#!/usr/bin/env bash
set -euo pipefail
# Local dev bootstrap.
cd "$(dirname "$0")/.."

echo "→ backend"
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

echo "→ frontend"
cd frontend
npm install
cd ..

echo "→ playwright"
cd playwright-runner
npm install
npx playwright install chromium
cd ..

echo "Done."
