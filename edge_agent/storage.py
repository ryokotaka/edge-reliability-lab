from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc TEXT NOT NULL,
  seq INTEGER NOT NULL,
  source TEXT NOT NULL,
  temperature_c REAL,
  humidity_pct REAL,
  pressure_hpa REAL,
  latency_ms REAL,
  status TEXT NOT NULL,
  fault_type TEXT NOT NULL,
  created_at_utc TEXT NOT NULL
);
"""


INSERT_SQL = """
INSERT INTO readings (
  ts_utc,
  seq,
  source,
  temperature_c,
  humidity_pct,
  pressure_hpa,
  latency_ms,
  status,
  fault_type,
  created_at_utc
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def init_db(conn: sqlite3.Connection, *, replace: bool = False) -> None:
    if replace:
        conn.execute("DROP TABLE IF EXISTS readings")
    conn.execute(SCHEMA_SQL)
    conn.commit()


def _optional_float(value: object) -> float | None:
    return None if value == "" else float(value)


def _row_to_record(raw: Mapping[str, object], created_at_utc: str) -> tuple[object, ...]:
    return (
        str(raw["ts_utc"]),
        int(raw["seq"]),
        str(raw["source"]),
        _optional_float(raw["temperature_c"]),
        _optional_float(raw["humidity_pct"]),
        _optional_float(raw["pressure_hpa"]),
        _optional_float(raw["latency_ms"]),
        str(raw["status"]),
        str(raw["fault_type"]),
        created_at_utc,
    )


def insert_readings(
    conn: sqlite3.Connection,
    readings: Iterable[Mapping[str, object]],
    *,
    created_at_utc: str | None = None,
) -> int:
    created_at = created_at_utc or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [_row_to_record(raw, created_at) for raw in readings]
    conn.executemany(INSERT_SQL, rows)
    conn.commit()
    return len(rows)


def write_rows_to_sqlite(
    readings: Iterable[Mapping[str, object]],
    db_path: Path,
    *,
    replace: bool = True,
) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        init_db(conn, replace=replace)
        return insert_readings(conn, readings)


def import_csv_to_sqlite(csv_path: Path, db_path: Path, *, replace: bool = True) -> int:
    with csv_path.open(newline="") as csv_file, sqlite3.connect(db_path) as conn:
        init_db(conn, replace=replace)
        reader = csv.DictReader(csv_file)
        return insert_readings(conn, reader)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import v0 readings CSV into SQLite.")
    parser.add_argument("csv_path", type=Path, help="Path to generated readings CSV.")
    parser.add_argument("db_path", type=Path, help="Output SQLite database path.")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append into an existing readings table instead of replacing it.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    count = import_csv_to_sqlite(args.csv_path, args.db_path, replace=not args.append)
    print(f"imported_rows={count}")


if __name__ == "__main__":
    main()
