from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_agent.tiny_model_stress import (
    DEFAULT_STRESS_SEEDS,
    run_tiny_model_stress_test,
)
from scripts.generate_synthetic_data import generate_rows


DEFAULT_START = datetime(2026, 4, 24, tzinfo=timezone.utc)


def _parse_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run v8 tiny model stress test across deterministic synthetic seeds."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/tiny_model_stress_experiment"))
    parser.add_argument("--seeds", type=_parse_seeds, default=DEFAULT_STRESS_SEEDS)
    parser.add_argument("--duration-minutes", type=int, default=30)
    parser.add_argument("--frequency-hz", type=int, default=1)
    parser.add_argument("--dropout-rate", type=float, default=0.03)
    parser.add_argument("--jitter-rate", type=float, default=0.05)
    parser.add_argument("--noisy-rate", type=float, default=0.01)
    parser.add_argument("--restart-gap-rate", type=float, default=0.005)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--positive-class-weight", type=float, default=20.0)
    parser.add_argument("--probability-threshold", type=float, default=0.5)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    seed_rows = [
        (
            seed,
            generate_rows(
                duration_minutes=args.duration_minutes,
                frequency_hz=args.frequency_hz,
                dropout_rate=args.dropout_rate,
                jitter_rate=args.jitter_rate,
                noisy_rate=args.noisy_rate,
                restart_gap_rate=args.restart_gap_rate,
                seed=seed,
                start_time=DEFAULT_START,
            ),
        )
        for seed in args.seeds
    ]
    result = run_tiny_model_stress_test(
        seed_rows,
        train_ratio=args.train_ratio,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        positive_class_weight=args.positive_class_weight,
        probability_threshold=args.probability_threshold,
    )
    result["data_generation"] = {
        "duration_minutes": args.duration_minutes,
        "frequency_hz": args.frequency_hz,
        "dropout_rate": args.dropout_rate,
        "jitter_rate": args.jitter_rate,
        "noisy_rate": args.noisy_rate,
        "restart_gap_rate": args.restart_gap_rate,
    }
    output_path = args.output_dir / "summary.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"wrote_summary={output_path}")


if __name__ == "__main__":
    main()
