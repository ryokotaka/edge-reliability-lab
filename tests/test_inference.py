from edge_agent.inference import (
    FloatAnomalyScorer,
    QuantizedAnomalyScorer,
    calibrate_stats,
    compute_detection_metrics,
    run_scorer,
)


def test_float_anomaly_scorer_detects_noisy_row() -> None:
    rows = [
        {
            "seq": str(seq),
            "temperature_c": "20.0",
            "humidity_pct": "50.0",
            "pressure_hpa": "1000.0",
            "status": "ok",
            "fault_type": "none",
        }
        for seq in range(10)
    ]
    rows.append(
        {
            "seq": "10",
            "temperature_c": "45.0",
            "humidity_pct": "95.0",
            "pressure_hpa": "1060.0",
            "status": "noisy",
            "fault_type": "noise",
        }
    )

    stats = calibrate_stats(rows, max_rows=10)
    scorer = FloatAnomalyScorer(stats, threshold=3.0)
    results = run_scorer(rows, scorer)
    metrics = compute_detection_metrics(results, model_state_bytes=scorer.state_size_bytes())

    assert metrics.true_anomaly_count == 1
    assert metrics.true_positive == 1
    assert metrics.false_negative == 0
    assert metrics.recall == 1.0


def test_quantized_scorer_uses_smaller_state_than_float_scorer() -> None:
    rows = [
        {
            "seq": str(seq),
            "temperature_c": str(20 + seq * 0.1),
            "humidity_pct": str(50 + seq * 0.1),
            "pressure_hpa": str(1000 + seq * 0.1),
            "status": "ok",
            "fault_type": "none",
        }
        for seq in range(20)
    ]

    stats = calibrate_stats(rows, max_rows=20)
    float_scorer = FloatAnomalyScorer(stats)
    quantized_scorer = QuantizedAnomalyScorer(stats)

    assert quantized_scorer.state_size_bytes() < float_scorer.state_size_bytes()
