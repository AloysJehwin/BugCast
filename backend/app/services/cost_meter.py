"""Cost accounting. The demo money shot lives here — keep it accurate."""
from __future__ import annotations

from dataclasses import dataclass

from app.utils.config import settings


@dataclass
class CostReport:
    local_tokens: int
    equivalent_gpt4o_input_tokens: int
    equivalent_gpt4o_output_tokens: int

    @property
    def local_usd(self) -> float:
        return (self.local_tokens / 1000.0) * settings.local_cost_per_1k

    @property
    def gpt4o_usd(self) -> float:
        return (
            (self.equivalent_gpt4o_input_tokens / 1000.0) * settings.gpt4o_cost_per_1k_input
            + (self.equivalent_gpt4o_output_tokens / 1000.0) * settings.gpt4o_cost_per_1k_output
        )

    @property
    def savings_factor(self) -> float:
        if self.local_usd == 0:
            return float("inf") if self.gpt4o_usd > 0 else 1.0
        return self.gpt4o_usd / self.local_usd

    def as_dict(self) -> dict[str, float | int]:
        return {
            "local_tokens": self.local_tokens,
            "local_usd": round(self.local_usd, 4),
            "gpt4o_usd": round(self.gpt4o_usd, 4),
            "savings_factor": round(self.savings_factor, 1),
        }
