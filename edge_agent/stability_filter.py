from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping

from edge_agent.inference import (
    DEFAULT_THRESHOLD,
    FloatAnomalyScorer,
    InferenceResult,
    calibrate_stats,
    compute_detection_metrics,
    run_scorer,
    usable_rows,
)


@dataclass(frozen=True)
class StabilityFilterSummary:
    mode: str
    evaluated_count: int
    true_anomaly_count: int
    predicted_anomaly_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float
    recall: float
    f1: float
    first_detected_anomaly_seq: int | None
    policy_state_bytes: int


def generate_false_positive_challenge_rows(
    *,
    total_rows: int = 120,
    transient_spike_sequences: tuple[int, ...] = (55, 72),
    sustained_anomaly_start: int = 95,
    sustained_anomaly_length: int = 6,
) -> list[dict[str, str]]:
    if total_rows <= 0:
        raise ValueError("total_rows must be positive")
    if sustained_anomaly_length <= 0:
        raise ValueError("sustained_anomaly_length must be positive")

    sustained_anomaly_end = sustained_anomaly_start + sustained_anomaly_length
    rows: list[dict[str, str]] = []
    for seq in range(total_rows):
        temperature_c = 22.0
        humidity_pct = 50.0
        pressure_hpa = 1000.0
        status = "ok"
        fault_type = "none"

        if seq in transient_spike_sequences:
            temperature_c += 6.0
            humidity_pct += 10.0
            pressure_hpa += 14.0
            fault_type = "transient_spike"
        elif sustained_anomaly_start <= seq < sustained_anomaly_end:
            temperature_c += 6.0
            humidity_pct += 10.0
            pressure_hpa += 14.0
            status = "noisy"
            fault_type = "noise"

        rows.append(
            {
                "ts_utc": f"2026-05-08T00:{seq // 60:02d}:{seq % 60:02d}Z",
                "seq": str(seq),
                "source": "synthetic",
                "temperature_c": f"{temperature_c:.3f}",
                "humidity_pct": f"{humidity_pct:.3f}",
                "pressure_hpa": f"{pressure_hpa:.3f}",
                "latency_ms": "20.000",
                "status": status,
                "fault_type": fault_type,
            }
        )
    return rows


def apply_consecutive_anomaly_filter(
    results: Iterable[InferenceResult],
    *,
    required_consecutive: int = 2,
) -> list[InferenceResult]:
    if required_consecutive < 1:
        raise ValueError("required_consecutive must be positive")

    streak = 0
    filtered_results: list[InferenceResult] = []
    for result in results:
        if result.is_anomaly:
            streak += 1
        else:
            streak = 0

        filtered_results.append(
            replace(
                result,
                mode=f"{result.mode}_hysteresis_{required_consecutive}",
                is_anomaly=streak >= required_consecutive,
            )
        )

    return filtered_results


def _first_detected_anomaly_seq(results: Iterable[InferenceResult]) -> int | None:
    for result in results:
        if result.is_anomaly and result.ground_truth_anomaly:
            return result.seq
    return None


def _summarize_results(
    *,
    mode: str,
    results: Iterable[InferenceResult],
    policy_state_bytes: int,
) -> StabilityFilterSummary:
    materialized = list(results)
    metrics = compute_detection_metrics(
        materialized,
        model_state_bytes=policy_state_bytes,
    )
    return StabilityFilterSummary(
        mode=mode,
        evaluated_count=metrics.evaluated_count,
        true_anomaly_count=metrics.true_anomaly_count,
        predicted_anomaly_count=metrics.predicted_anomaly_count,
        true_positive=metrics.true_positive,
        false_positive=metrics.false_positive,
        false_negative=metrics.false_negative,
        precision=metrics.precision,
        recall=metrics.recall,
        f1=metrics.f1,
        first_detected_anomaly_seq=_first_detected_anomaly_seq(materialized),
        policy_state_bytes=policy_state_bytes,
    )


def run_stability_filter_comparison(
    rows: Iterable[Mapping[str, object]] | None = None,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    calibration_rows: int = 40,
    required_consecutive: int = 2,
) -> dict[str, object]:
    materialized = list(rows) if rows is not None else generate_false_positive_challenge_rows()
    stats = calibrate_stats(materialized, max_rows=calibration_rows)
    scorer = FloatAnomalyScorer(stats, threshold=threshold)

    raw_results = run_scorer(materialized, scorer)
    filtered_results = apply_consecutive_anomaly_filter(
        raw_results,
        required_consecutive=required_consecutive,
    )
    raw_summary = _summarize_results(
        mode="threshold_only",
        results=raw_results,
        policy_state_bytes=scorer.state_size_bytes(),
    )
    filtered_summary = _summarize_results(
        mode=f"hysteresis_{required_consecutive}",
        results=filtered_results,
        policy_state_bytes=scorer.state_size_bytes() + 1,
    )

    detection_delay = None
    if (
        raw_summary.first_detected_anomaly_seq is not None
        and filtered_summary.first_detected_anomaly_seq is not None
    ):
        detection_delay = (
            filtered_summary.first_detected_anomaly_seq
            - raw_summary.first_detected_anomaly_seq
        )

    return {
        "threshold": threshold,
        "calibration_rows": calibration_rows,
        "required_consecutive": required_consecutive,
        "transient_spike_sequences": [
            int(row["seq"])
            for row in materialized
            if row.get("fault_type") == "transient_spike"
        ],
        "sustained_anomaly_sequences": [
            int(row["seq"]) for row in materialized if row.get("fault_type") == "noise"
        ],
        "threshold_only": asdict(raw_summary),
        "hysteresis": asdict(filtered_summary),
        "false_positive_reduction": raw_summary.false_positive - filtered_summary.false_positive,
        "detection_delay_samples": detection_delay,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare threshold-only anomaly alerts against a small hysteresis filter."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/filtering_experiment"))
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--calibration-rows", type=int, default=40)
    parser.add_argument("--required-consecutive", type=int, default=2)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = run_stability_filter_comparison(
        threshold=args.threshold,
        calibration_rows=args.calibration_rows,
        required_consecutive=args.required_consecutive,
    )
    output_path = args.output_dir / "summary.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"wrote_summary={output_path}")


if __name__ == "__main__":
    main()
