#!/usr/bin/env bash
set -euo pipefail
# Provision helper — run on AMD Developer Cloud after `ssh` in.
sudo apt-get update
sudo apt-get install -y ffmpeg git python3.11 python3.11-venv build-essential
python3.11 -m venv ~/venv
source ~/venv/bin/activate
pip install --upgrade pip
pip install vllm rocm-smi torch --index-url https://download.pytorch.org/whl/rocm6.2 || true
echo "Done. Next: launch VLM with ml/vlm/serve.py CMD."
