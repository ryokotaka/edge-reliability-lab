from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_agent.resource_budget import (
    ResourceBudget,
    load_json,
    run_resource_budget_comparison,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run v9 resource budget gate for tiny-model stress results."
    )
    parser.add_argument(
        "--stress-summary",
        type=Path,
        default=Path("data/tiny_model_stress_experiment/summary.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/resource_budget_experiment"))
    parser.add_argument("--max-model-state-bytes", type=int, default=64)
    parser.add_argument("--min-f1", type=float, default=0.90)
    parser.add_argument("--max-false-negative-rate", type=float, default=0.10)
    parser.add_argument("--max-false-positive-count", type=int, default=0)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    budget = ResourceBudget(
        max_model_state_bytes=args.max_model_state_bytes,
        min_f1=args.min_f1,
        max_false_negative_rate=args.max_false_negative_rate,
        max_false_positive_count=args.max_false_positive_count,
    )
    result = run_resource_budget_comparison(
        load_json(args.stress_summary),
        budget=budget,
    )
    output_path = args.output_dir / "summary.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"wrote_summary={output_path}")


if __name__ == "__main__":
    main()
