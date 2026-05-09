from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence

from edge_agent.inference import load_csv_rows
from edge_agent.tiny_model import run_tiny_model_comparison


DEFAULT_STRESS_SEEDS = (11, 23, 42, 71, 101, 133, 191)
MODEL_KEYS = ("statistical_scorer", "learned_float_like", "learned_quantized_like")


def compact_metrics(metrics: Mapping[str, object]) -> dict[str, object]:
    return {
        "evaluated_count": metrics["evaluated_count"],
        "true_anomaly_count": metrics["true_anomaly_count"],
        "predicted_anomaly_count": metrics["predicted_anomaly_count"],
        "true_positive": metrics["true_positive"],
        "false_positive": metrics["false_positive"],
        "false_negative": metrics["false_negative"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "model_state_bytes": metrics["model_state_bytes"],
    }


def aggregate_model_metrics(per_seed: Sequence[Mapping[str, object]], model_key: str) -> dict[str, object]:
    sections = [seed_result[model_key] for seed_result in per_seed]
    true_positive = sum(int(section["true_positive"]) for section in sections)
    false_positive = sum(int(section["false_positive"]) for section in sections)
    false_negative = sum(int(section["false_negative"]) for section in sections)
    true_anomaly_count = sum(int(section["true_anomaly_count"]) for section in sections)
    predicted_anomaly_count = sum(int(section["predicted_anomaly_count"]) for section in sections)
    precision = true_positive / predicted_anomaly_count if predicted_anomaly_count else 0.0
    recall = true_positive / true_anomaly_count if true_anomaly_count else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )
    seed_f1_values = [float(section["f1"]) for section in sections]
    state_sizes = [int(section["model_state_bytes"]) for section in sections]

    return {
        "true_anomaly_count": true_anomaly_count,
        "predicted_anomaly_count": predicted_anomaly_count,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mean_seed_f1": mean(seed_f1_values),
        "min_seed_f1": min(seed_f1_values),
        "model_state_bytes": state_sizes[0] if len(set(state_sizes)) == 1 else state_sizes,
    }


def run_tiny_model_stress_test(
    seed_rows: Iterable[tuple[int, Iterable[Mapping[str, object]]]],
    *,
    train_ratio: float = 0.7,
    epochs: int = 400,
    learning_rate: float = 0.01,
    positive_class_weight: float = 20.0,
    probability_threshold: float = 0.5,
) -> dict[str, object]:
    per_seed: list[dict[str, object]] = []
    for seed, rows in seed_rows:
        comparison = run_tiny_model_comparison(
            rows,
            train_ratio=train_ratio,
            epochs=epochs,
            learning_rate=learning_rate,
            positive_class_weight=positive_class_weight,
            probability_threshold=probability_threshold,
        )
        seed_result = {
            "seed": seed,
            "train_count": comparison["train_count"],
            "test_count": comparison["test_count"],
            "test_anomaly_count": comparison["learned_quantized_like"]["true_anomaly_count"],
        }
        for model_key in MODEL_KEYS:
            seed_result[model_key] = compact_metrics(comparison[model_key])
        per_seed.append(seed_result)

    if not per_seed:
        raise ValueError("at least one seed result is required")

    return {
        "seeds": [result["seed"] for result in per_seed],
        "seed_count": len(per_seed),
        "train_ratio": train_ratio,
        "epochs": epochs,
        "learning_rate": learning_rate,
        "positive_class_weight": positive_class_weight,
        "probability_threshold": probability_threshold,
        "total_test_count": sum(int(result["test_count"]) for result in per_seed),
        "total_test_anomaly_count": sum(int(result["test_anomaly_count"]) for result in per_seed),
        "per_seed": per_seed,
        "aggregate": {
            model_key: aggregate_model_metrics(per_seed, model_key)
            for model_key in MODEL_KEYS
        },
    }


def _parse_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate tiny model metrics across multiple CSV files."
    )
    parser.add_argument("csv_paths", type=Path, nargs="+")
    parser.add_argument(
        "--seeds",
        type=_parse_seeds,
        default=DEFAULT_STRESS_SEEDS,
        help="Comma-separated seed labels matching csv_paths.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if len(args.csv_paths) != len(args.seeds):
        raise SystemExit("csv_paths count must match seed count")
    seed_rows = [
        (seed, load_csv_rows(csv_path))
        for seed, csv_path in zip(args.seeds, args.csv_paths)
    ]
    result = run_tiny_model_stress_test(seed_rows)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
