from edge_agent.stability_filter import (
    apply_consecutive_anomaly_filter,
    generate_false_positive_challenge_rows,
    run_stability_filter_comparison,
)
from edge_agent.inference import FloatAnomalyScorer, calibrate_stats, run_scorer


def test_consecutive_filter_removes_single_sample_false_positive() -> None:
    rows = generate_false_positive_challenge_rows(
        transient_spike_sequences=(55,),
        sustained_anomaly_start=80,
        sustained_anomaly_length=4,
    )
    stats = calibrate_stats(rows, max_rows=40)
    scorer = FloatAnomalyScorer(stats, threshold=3.0)
    raw_results = run_scorer(rows, scorer)
    filtered_results = apply_consecutive_anomaly_filter(raw_results, required_consecutive=2)

    raw_transient = next(result for result in raw_results if result.seq == 55)
    filtered_transient = next(result for result in filtered_results if result.seq == 55)
    first_filtered_true = next(
        result for result in filtered_results if result.is_anomaly and result.ground_truth_anomaly
    )

    assert raw_transient.is_anomaly
    assert not raw_transient.ground_truth_anomaly
    assert not filtered_transient.is_anomaly
    assert first_filtered_true.seq == 81


def test_stability_filter_comparison_reports_tradeoff() -> None:
    result = run_stability_filter_comparison(required_consecutive=2)

    raw = result["threshold_only"]
    filtered = result["hysteresis"]

    assert raw["false_positive"] == 2
    assert filtered["false_positive"] == 0
    assert result["false_positive_reduction"] == 2
    assert result["detection_delay_samples"] == 1
    assert filtered["recall"] < raw["recall"]
