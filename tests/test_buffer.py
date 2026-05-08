import sqlite3

from edge_agent.buffer import LocalRecoveryBuffer
from edge_agent.metrics import load_rows_from_sqlite
from edge_agent.storage import init_db, write_rows_to_sqlite


def test_local_recovery_buffer_flushes_pending_rows_to_sqlite(tmp_path) -> None:
    db_path = tmp_path / "readings.sqlite"
    buffer_path = tmp_path / "pending.jsonl"
    checkpoint_path = tmp_path / "checkpoint.json"
    direct_row = {
        "ts_utc": "2026-04-24T00:00:00Z",
        "seq": "0",
        "source": "synthetic",
        "temperature_c": "20.0",
        "humidity_pct": "40.0",
        "pressure_hpa": "1000.0",
        "latency_ms": "20.0",
        "status": "ok",
        "fault_type": "none",
    }
    buffered_row = dict(direct_row, seq="1", latency_ms="25.0")

    with sqlite3.connect(db_path) as conn:
        init_db(conn, replace=True)
    write_rows_to_sqlite([direct_row], db_path, replace=False)

    recovery_buffer = LocalRecoveryBuffer(buffer_path, checkpoint_path)
    recovery_buffer.append(buffered_row)
    assert len(recovery_buffer.load_pending()) == 1

    flushed = recovery_buffer.flush_to_sqlite(db_path)

    assert flushed == 1
    assert recovery_buffer.load_pending() == []
    assert [row["seq"] for row in load_rows_from_sqlite(db_path)] == [0, 1]
    assert '"pending_count": 0' in checkpoint_path.read_text()
