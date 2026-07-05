from __future__ import annotations

from app.services.cost_meter import CostReport


class TestCostReport:
    def test_zero_local_infinite_savings(self) -> None:
        r = CostReport(local_tokens=1000, equivalent_gpt4o_input_tokens=100000, equivalent_gpt4o_output_tokens=50000)
        # local_cost_per_1k defaults to 0.0 → local_usd == 0.0
        assert r.local_usd == 0.0
        assert r.gpt4o_usd > 0
        assert r.savings_factor == float("inf")

    def test_gpt4o_math(self) -> None:
        # 10K in × $0.005/1K + 5K out × $0.015/1K = $0.05 + $0.075 = $0.125
        r = CostReport(local_tokens=0, equivalent_gpt4o_input_tokens=10_000, equivalent_gpt4o_output_tokens=5_000)
        assert r.gpt4o_usd == 0.125

    def test_as_dict_shape(self) -> None:
        r = CostReport(local_tokens=1000, equivalent_gpt4o_input_tokens=1000, equivalent_gpt4o_output_tokens=1000)
        d = r.as_dict()
        assert set(d.keys()) == {"local_tokens", "local_usd", "gpt4o_usd", "savings_factor"}
