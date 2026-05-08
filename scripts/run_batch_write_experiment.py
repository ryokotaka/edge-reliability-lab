from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_agent.batching import load_csv_rows, run_batch_write_comparison


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run v4 SQLite batch-write comparison.")
    parser.add_argument("--csv-path", type=Path, default=Path("data/sample.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/batching_experiment"))
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = run_batch_write_comparison(
        load_csv_rows(args.csv_path),
        args.output_dir,
        batch_size=args.batch_size,
    )
    output_path = args.output_dir / "summary.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"wrote_summary={output_path}")


if __name__ == "__main__":
    main()
