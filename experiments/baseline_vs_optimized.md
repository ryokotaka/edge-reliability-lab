# Baseline vs Optimized

## v1 Local Buffer / Checkpoint Recovery

The first optimization experiment simulates a SQLite write failure for sequence
`600..719`. The baseline direct-write path loses those rows. The optimized path
writes them to a local JSONL buffer, records a checkpoint, and flushes them to
SQLite after recovery.

| Metric | Baseline direct write | Buffered recovery | Interpretation |
| --- | ---: | ---: | --- |
| observed samples | 1680 | 1800 | local buffer recovered the write-failure window |
| missing rate | 0.0989 | 0.0344 | recovery removed absent sequence slots |
| p95 latency | 125.789 ms | 132.089 ms | recovered rows include original jitter distribution |
| uptime ratio | 0.8900 | 0.9539 | recovered ok rows restore uptime accounting |
| recovery loss | 120 samples | 0 samples | checkpoint recovery effect |

## Planned Later Comparisons

| Metric | Baseline | Optimized | Interpretation |
| --- | ---: | ---: | --- |
| inference latency | TBD ms | TBD ms | quantization effect |
| memory usage | TBD MB | TBD MB | constrained-device fit |
| accuracy / detection quality | TBD | TBD | lightweight inference trade-off |
