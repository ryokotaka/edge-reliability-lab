from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable, Mapping, Sequence


SIGNALS = ("temperature_c", "humidity_pct", "pressure_hpa")
DEFAULT_THRESHOLD = 3.0


@dataclass(frozen=True)
class CalibrationStats:
    means: dict[str, float]
    stddevs: dict[str, float]


@dataclass(frozen=True)
class InferenceResult:
    seq: int
    mode: str
    score: float
    is_anomaly: bool
    ground_truth_anomaly: bool
    latency_ms: float


@dataclass(frozen=True)
class DetectionMetrics:
    evaluated_count: int
    true_anomaly_count: int
    predicted_anomaly_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float
    recall: float
    f1: float
    avg_inference_latency_ms: float
    p95_inference_latency_ms: float | None
    model_state_bytes: int


def parse_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def usable_rows(rows: Iterable[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return [
        row
        for row in rows
        if row.get("status") != "missing"
        and all(parse_float(row.get(signal)) is not None for signal in SIGNALS)
    ]


def calibrate_stats(
    rows: Iterable[Mapping[str, object]],
    *,
    max_rows: int = 300,
) -> CalibrationStats:
    normal_rows = [
        row
        for row in usable_rows(rows)
        if row.get("status") == "ok" and row.get("fault_type") == "none"
    ][:max_rows]
    if len(normal_rows) < 2:
        raise ValueError("at least two normal rows are required for calibration")

    means: dict[str, float] = {}
    stddevs: dict[str, float] = {}
    for signal in SIGNALS:
        values = [float(parse_float(row[signal])) for row in normal_rows]
        means[signal] = mean(values)
        stddev = pstdev(values)
        stddevs[signal] = stddev if stddev > 0 else 1.0

    return CalibrationStats(means=means, stddevs=stddevs)


def anomaly_score(row: Mapping[str, object], stats: CalibrationStats) -> float:
    scores = []
    for signal in SIGNALS:
        value = parse_float(row.get(signal))
        if value is None:
            continue
        scores.append(abs(value - stats.means[signal]) / stats.stddevs[signal])
    return max(scores) if scores else 0.0


class FloatAnomalyScorer:
    mode = "float32_like"

    def __init__(self, stats: CalibrationStats, threshold: float = DEFAULT_THRESHOLD) -> None:
        self.stats = stats
        self.threshold = threshold

    def predict(self, row: Mapping[str, object]) -> InferenceResult:
        start = time.perf_counter()
        score = anomaly_score(row, self.stats)
        latency_ms = (time.perf_counter() - start) * 1000
        return InferenceResult(
            seq=int(row["seq"]),
            mode=self.mode,
            score=score,
            is_anomaly=score >= self.threshold,
            ground_truth_anomaly=row.get("status") == "noisy" or row.get("fault_type") == "noise",
            latency_ms=latency_ms,
        )

    def state_size_bytes(self) -> int:
        # Three means and three stddevs as Python-like double precision values.
        return len(SIGNALS) * 2 * 8


class QuantizedAnomalyScorer:
    mode = "int8_quantized_like"

    def __init__(
        self,
        stats: CalibrationStats,
        threshold: float = DEFAULT_THRESHOLD,
        scale: int = 10,
    ) -> None:
        self.threshold = threshold
        self.scale = scale
        self.means = {signal: int(round(value * scale)) for signal, value in stats.means.items()}
        self.stddevs = {
            signal: max(1, int(round(value * scale))) for signal, value in stats.stddevs.items()
        }

    def predict(self, row: Mapping[str, object]) -> InferenceResult:
        start = time.perf_counter()
        score = self._score(row)
        latency_ms = (time.perf_counter() - start) * 1000
        return InferenceResult(
            seq=int(row["seq"]),
            mode=self.mode,
            score=score,
            is_anomaly=score >= self.threshold,
            ground_truth_anomaly=row.get("status") == "noisy" or row.get("fault_type") == "noise",
            latency_ms=latency_ms,
        )

    def _score(self, row: Mapping[str, object]) -> float:
        scores = []
        for signal in SIGNALS:
            value = parse_float(row.get(signal))
            if value is None:
                continue
            quantized_value = int(round(value * self.scale))
            scores.append(abs(quantized_value - self.means[signal]) / self.stddevs[signal])
        return max(scores) if scores else 0.0

    def state_size_bytes(self) -> int:
        # Three means and three stddevs as one-byte quantized parameters.
        return len(SIGNALS) * 2


def nearest_rank_percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile / 100) * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def run_scorer(
    rows: Iterable[Mapping[str, object]],
    scorer: FloatAnomalyScorer | QuantizedAnomalyScorer,
) -> list[InferenceResult]:
    return [scorer.predict(row) for row in usable_rows(rows)]


def compute_detection_metrics(
    results: Iterable[InferenceResult],
    *,
    model_state_bytes: int,
) -> DetectionMetrics:
    materialized = list(results)
    true_positive = sum(
        1 for result in materialized if result.is_anomaly and result.ground_truth_anomaly
    )
    false_positive = sum(
        1 for result in materialized if result.is_anomaly and not result.ground_truth_anomaly
    )
    false_negative = sum(
        1 for result in materialized if not result.is_anomaly and result.ground_truth_anomaly
    )
    true_anomaly_count = sum(1 for result in materialized if result.ground_truth_anomaly)
    predicted_anomaly_count = sum(1 for result in materialized if result.is_anomaly)
    precision = true_positive / predicted_anomaly_count if predicted_anomaly_count else 0.0
    recall = true_positive / true_anomaly_count if true_anomaly_count else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )
    latencies = [result.latency_ms for result in materialized]

    return DetectionMetrics(
        evaluated_count=len(materialized),
        true_anomaly_count=true_anomaly_count,
        predicted_anomaly_count=predicted_anomaly_count,
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        precision=precision,
        recall=recall,
        f1=f1,
        avg_inference_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
        p95_inference_latency_ms=nearest_rank_percentile(latencies, 95),
        model_state_bytes=model_state_bytes,
    )


def load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def run_inference_comparison(
    rows: Iterable[Mapping[str, object]],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    calibration_rows: int = 300,
    quantization_scale: int = 10,
) -> dict[str, object]:
    materialized = list(rows)
    stats = calibrate_stats(materialized, max_rows=calibration_rows)

    float_scorer = FloatAnomalyScorer(stats, threshold=threshold)
    quantized_scorer = QuantizedAnomalyScorer(
        stats,
        threshold=threshold,
        scale=quantization_scale,
    )

    float_results = run_scorer(materialized, float_scorer)
    quantized_results = run_scorer(materialized, quantized_scorer)
    float_metrics = compute_detection_metrics(
        float_results,
        model_state_bytes=float_scorer.state_size_bytes(),
    )
    quantized_metrics = compute_detection_metrics(
        quantized_results,
        model_state_bytes=quantized_scorer.state_size_bytes(),
    )

    return {
        "threshold": threshold,
        "calibration_rows": calibration_rows,
        "quantization_scale": quantization_scale,
        "float32_like": asdict(float_metrics),
        "int8_quantized_like": asdict(quantized_metrics),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare float-like and quantized lightweight anomaly scoring."
    )
    parser.add_argument("csv_path", type=Path, nargs="?", default=Path("data/sample.csv"))
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--calibration-rows", type=int, default=300)
    parser.add_argument("--quantization-scale", type=int, default=10)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = run_inference_comparison(
        load_csv_rows(args.csv_path),
        threshold=args.threshold,
        calibration_rows=args.calibration_rows,
        quantization_scale=args.quantization_scale,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
