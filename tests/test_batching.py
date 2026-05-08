import sqlite3

from edge_agent.batching import chunked, write_rows_in_batches


def _row(seq: int) -> dict[str, str]:
    return {
        "ts_utc": f"2026-04-24T00:00:{seq:02d}Z",
        "seq": str(seq),
        "source": "synthetic",
        "temperature_c": "22.0",
        "humidity_pct": "50.0",
        "pressure_hpa": "1000.0",
        "latency_ms": "20.0",
        "status": "ok",
        "fault_type": "none",
    }


def test_chunked_splits_rows_by_batch_size() -> None:
    rows = [_row(seq) for seq in range(5)]

    batches = chunked(rows, batch_size=2)

    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_batch_writes_reduce_insert_and_commit_calls(tmp_path) -> None:
    rows = [_row(seq) for seq in range(5)]
    direct_db = tmp_path / "direct.sqlite"
    batched_db = tmp_path / "batched.sqlite"

    direct = write_rows_in_batches(rows, direct_db, mode="direct", batch_size=1)
    batched = write_rows_in_batches(rows, batched_db, mode="batched", batch_size=2)

    assert direct.rows_written == 5
    assert batched.rows_written == 5
    assert direct.insert_calls == 5
    assert batched.insert_calls == 3
    assert direct.commit_count == 5
    assert batched.commit_count == 3

    with sqlite3.connect(batched_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    assert count == 5
