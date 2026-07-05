from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # runtime
    upload_dir: str = "./uploads"
    frames_dir: str = "./frames"
    outputs_dir: str = "./samples/outputs"
    cors_origins: list[str] = ["http://localhost:3000"]

    # pipeline knobs
    extract_fps: int = 2
    ssim_threshold: float = 0.92
    max_key_frames: int = 5
    max_video_seconds: int = 90

    # models
    vlm_endpoint: str = "http://localhost:8001/v1"
    vlm_model: str = "Qwen/Qwen2-VL-72B-Instruct"
    coder_endpoint: str = "http://localhost:8002/v1"
    coder_model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"

    # fallback
    fireworks_api_key: str = ""
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"

    # cost accounting (USD per 1K tokens, indicative)
    local_cost_per_1k: float = 0.0
    gpt4o_cost_per_1k_input: float = 0.005
    gpt4o_cost_per_1k_output: float = 0.015


settings = Settings()
