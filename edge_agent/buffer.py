from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from edge_agent.storage import write_rows_to_sqlite


class LocalRecoveryBuffer:
    """JSONL-backed local buffer for readings that cannot be written immediately."""

    def __init__(self, buffer_path: Path, checkpoint_path: Path) -> None:
        self.buffer_path = buffer_path
        self.checkpoint_path = checkpoint_path
        self.buffer_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, reading: Mapping[str, object]) -> None:
        with self.buffer_path.open("a") as buffer_file:
            buffer_file.write(json.dumps(dict(reading), sort_keys=True) + "\n")
        self._write_checkpoint(
            {
                "last_buffered_seq": int(reading["seq"]),
                "pending_count": len(self.load_pending()),
            }
        )

    def load_pending(self) -> list[dict[str, object]]:
        if not self.buffer_path.exists():
            return []
        with self.buffer_path.open() as buffer_file:
            return [json.loads(line) for line in buffer_file if line.strip()]

    def flush_to_sqlite(self, db_path: Path) -> int:
        pending = self.load_pending()
        if not pending:
            self._write_checkpoint({"pending_count": 0, "flushed_count": 0})
            return 0

        inserted = write_rows_to_sqlite(pending, db_path, replace=False)
        self.buffer_path.unlink(missing_ok=True)
        self._write_checkpoint(
            {
                "last_flushed_seq": int(pending[-1]["seq"]),
                "pending_count": 0,
                "flushed_count": inserted,
            }
        )
        return inserted

    def _write_checkpoint(self, payload: Mapping[str, object]) -> None:
        previous: dict[str, object] = {}
        if self.checkpoint_path.exists():
            previous = json.loads(self.checkpoint_path.read_text())
        previous.update(payload)
        self.checkpoint_path.write_text(json.dumps(previous, indent=2, sort_keys=True) + "\n")

