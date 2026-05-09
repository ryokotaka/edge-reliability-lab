from edge_agent.resource_budget import (
    ResourceBudget,
    run_resource_budget_comparison,
)


def _stress_summary() -> dict[str, object]:
    return {
        "seed_count": 7,
        "total_test_anomaly_count": 41,
        "aggregate": {
            "statistical_scorer": {
                "model_state_bytes": 48,
                "f1": 0.8767,
                "false_negative": 9,
                "false_positive": 0,
                "true_anomaly_count": 41,
            },
            "learned_float_like": {
                "model_state_bytes": 104,
                "f1": 0.9487,
                "false_negative": 4,
                "false_positive": 0,
                "true_anomaly_count": 41,
            },
            "learned_quantized_like": {
                "model_state_bytes": 42,
                "f1": 0.9487,
                "false_negative": 4,
                "false_positive": 0,
                "true_anomaly_count": 41,
            },
        },
    }


def test_resource_budget_recommends_quantized_tiny_model() -> None:
    summary = run_resource_budget_comparison(_stress_summary())

    assert summary["recommended_model"] == "learned_quantized_like"
    assert summary["models"]["learned_quantized_like"]["passes_all"] is True
    assert summary["models"]["learned_float_like"]["passes_state_budget"] is False
    assert summary["models"]["statistical_scorer"]["passes_f1_budget"] is False


def test_resource_budget_reports_false_negative_rate_failure() -> None:
    summary = run_resource_budget_comparison(
        _stress_summary(),
        budget=ResourceBudget(max_false_negative_rate=0.05),
    )

    assert summary["recommended_model"] is None
    assert "false_negative_rate" in (
        summary["models"]["learned_quantized_like"]["fail_reasons"]
    )
