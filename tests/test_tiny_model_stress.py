from edge_agent.tiny_model_stress import run_tiny_model_stress_test


def _row(seq: int, *, noisy: bool = False) -> dict[str, str]:
    if noisy:
        return {
            "seq": str(seq),
            "temperature_c": "44.0" if seq % 2 == 0 else "6.0",
            "humidity_pct": "92.0" if seq % 2 == 0 else "14.0",
            "pressure_hpa": "1065.0" if seq % 2 == 0 else "940.0",
            "latency_ms": "220.0",
            "status": "noisy",
            "fault_type": "noise",
        }
    return {
        "seq": str(seq),
        "temperature_c": str(22.0 + (seq % 5) * 0.2),
        "humidity_pct": str(48.0 + (seq % 7) * 0.3),
        "pressure_hpa": str(1002.0 + (seq % 3) * 0.4),
        "latency_ms": str(28.0 + (seq % 4) * 1.5),
        "status": "ok",
        "fault_type": "none",
    }


def _rows() -> list[dict[str, str]]:
    noisy_sequences = {12, 36, 64, 72}
    return [_row(seq, noisy=seq in noisy_sequences) for seq in range(80)]


def _shifted_rows(offset: int) -> list[dict[str, str]]:
    rows = []
    for row in _rows():
        shifted = dict(row)
        shifted["seq"] = str(int(row["seq"]) + offset)
        if shifted["temperature_c"]:
            shifted["temperature_c"] = str(float(shifted["temperature_c"]) + offset * 0.001)
        rows.append(shifted)
    return rows


def test_tiny_model_stress_aggregates_multiple_seeds() -> None:
    summary = run_tiny_model_stress_test(
        [
            (101, _rows()),
            (202, _shifted_rows(100)),
        ],
        epochs=80,
    )

    assert summary["seed_count"] == 2
    assert summary["total_test_anomaly_count"] >= 2
    assert len(summary["per_seed"]) == 2
    assert summary["aggregate"]["learned_quantized_like"]["true_anomaly_count"] == (
        sum(seed["test_anomaly_count"] for seed in summary["per_seed"])
    )


def test_tiny_model_stress_reports_quantized_state_reduction() -> None:
    summary = run_tiny_model_stress_test([(101, _rows())], epochs=80)

    assert (
        summary["aggregate"]["learned_quantized_like"]["model_state_bytes"]
        < summary["aggregate"]["learned_float_like"]["model_state_bytes"]
    )
    assert summary["aggregate"]["learned_quantized_like"]["min_seed_f1"] <= (
        summary["aggregate"]["learned_quantized_like"]["mean_seed_f1"]
    )
