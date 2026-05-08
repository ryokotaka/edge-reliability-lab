from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from edge_agent.storage import INSERT_SQL, init_db, row_to_record


@dataclass(frozen=True)
class BatchWriteMetrics:
    mode: str
    rows_written: int
    batch_size: int
    insert_calls: int
    commit_count: int
    elapsed_ms: float
    rows_per_insert_call: float
    rows_per_commit: float


def load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def chunked(rows: Sequence[Mapping[str, object]], batch_size: int) -> list[list[Mapping[str, object]]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    return [list(rows[index : index + batch_size]) for index in range(0, len(rows), batch_size)]


def write_rows_in_batches(
    rows: Iterable[Mapping[str, object]],
    db_path: Path,
    *,
    mode: str,
    batch_size: int,
    replace: bool = True,
) -> BatchWriteMetrics:
    materialized = list(rows)
    batches = chunked(materialized, batch_size)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    start = time.perf_counter()
    with sqlite3.connect(db_path) as conn:
        init_db(conn, replace=replace)
        insert_calls = 0
        commit_count = 0
        for batch in batches:
            records = [row_to_record(row, created_at) for row in batch]
            conn.executemany(INSERT_SQL, records)
            insert_calls += 1
            conn.commit()
            commit_count += 1
    elapsed_ms = (time.perf_counter() - start) * 1000

    rows_written = len(materialized)
    return BatchWriteMetrics(
        mode=mode,
        rows_written=rows_written,
        batch_size=batch_size,
        insert_calls=insert_calls,
        commit_count=commit_count,
        elapsed_ms=elapsed_ms,
        rows_per_insert_call=rows_written / insert_calls if insert_calls else 0.0,
        rows_per_commit=rows_written / commit_count if commit_count else 0.0,
    )


def run_batch_write_comparison(
    rows: Iterable[Mapping[str, object]],
    output_dir: Path,
    *,
    batch_size: int = 100,
) -> dict[str, object]:
    materialized = list(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    direct_db = output_dir / "direct_per_row.sqlite"
    batched_db = output_dir / f"batched_{batch_size}.sqlite"

    for path in (direct_db, batched_db):
        path.unlink(missing_ok=True)

    direct = write_rows_in_batches(
        materialized,
        direct_db,
        mode="direct_per_row",
        batch_size=1,
        replace=True,
    )
    batched = write_rows_in_batches(
        materialized,
        batched_db,
        mode=f"batched_{batch_size}",
        batch_size=batch_size,
        replace=True,
    )

    return {
        "rows": len(materialized),
        "batch_size": batch_size,
        "direct_per_row": asdict(direct),
        "batched": asdict(batched),
        "insert_call_reduction": direct.insert_calls - batched.insert_calls,
        "commit_reduction": direct.commit_count - batched.commit_count,
        "elapsed_ms_change": batched.elapsed_ms - direct.elapsed_ms,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare direct SQLite writes against batched writes.")
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
