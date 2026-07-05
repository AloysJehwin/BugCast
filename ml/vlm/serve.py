"""vLLM launcher for Qwen2-VL-72B on AMD MI300X.

Usage:
    ROCM_VISIBLE_DEVICES=0 bash scripts/serve_vlm.sh

This is a reference command list — run pieces manually in day 2 until stable.
"""

CMD = [
    "python", "-m", "vllm.entrypoints.openai.api_server",
    "--model", "Qwen/Qwen2-VL-72B-Instruct",
    "--port", "8001",
    "--max-model-len", "16384",
    "--gpu-memory-utilization", "0.90",
    "--trust-remote-code",
    "--dtype", "bfloat16",
]

if __name__ == "__main__":
    print(" ".join(CMD))
