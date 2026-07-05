"""vLLM launcher for Qwen2.5-Coder-32B on AMD MI300X (co-resident with VLM)."""

CMD = [
    "python", "-m", "vllm.entrypoints.openai.api_server",
    "--model", "Qwen/Qwen2.5-Coder-32B-Instruct",
    "--port", "8002",
    "--max-model-len", "8192",
    "--gpu-memory-utilization", "0.35",
    "--dtype", "bfloat16",
]

if __name__ == "__main__":
    print(" ".join(CMD))
