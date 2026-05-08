from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_agent.stability_filter import run_stability_filter_comparison


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run v5 stability filter comparison for transient false positives."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/filtering_experiment"))
    parser.add_argument("--threshold", type=float, default=3.0)
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
