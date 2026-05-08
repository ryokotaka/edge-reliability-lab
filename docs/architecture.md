# Architecture

```text
synthetic sensor data
  -> CSV
  -> SQLite readings table
  -> reliability metrics
  -> lightweight inference
  -> software optimization
  -> experiment log
```

v0 stops at CSV, SQLite, and reliability metrics. Lightweight inference and
optimization are planned after the measurement pipeline is reproducible.

v1 adds a local JSONL recovery buffer:

```text
synthetic sensor data
  -> simulated SQLite write failure
  -> local recovery buffer
  -> checkpoint
  -> SQLite flush after recovery
  -> recovery_loss comparison
```
