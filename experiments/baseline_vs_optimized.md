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
| inference latency on Raspberry Pi | TBD ms | TBD ms | quantization effect on target hardware |
| memory usage on Raspberry Pi | TBD MB | TBD MB | constrained-device fit |
| adaptive sampling CPU / power | TBD | TBD | sampling trade-off |

## v2 Float-like vs Quantized-like Anomaly Scoring

The second optimization experiment uses `status = noisy` as the ground-truth anomaly
label. It calibrates normal environmental ranges from synthetic `ok` rows and compares
float-like scoring with quantized-like scoring.

| Metric | Float-like scoring | Quantized-like scoring | Interpretation |
| --- | ---: | ---: | --- |
| evaluated samples | 1738 | 1738 | missing rows are excluded from inference |
| true anomalies | 13 | 13 | synthetic noisy rows |
| true positives | 12 | 12 | same detected anomalies |
| false positives | 0 | 0 | no normal rows flagged |
| false negatives | 1 | 1 | one noisy row below threshold |
| precision | 1.0000 | 1.0000 | no false positives |
| recall | 0.9231 | 0.9231 | one missed noisy row |
| F1 | 0.9600 | 0.9600 | detection quality preserved |
| p95 inference latency | ~0.002 ms | ~0.001 ms | Python-level timing only |
| model state size | 48 bytes | 6 bytes | quantized-like state is smaller |

Interpretation:

```text
Quantized-like scoring preserved detection quality and reduced stored model state
in this small synthetic benchmark. Timing must be re-measured on Raspberry Pi before
claiming target-device latency improvement.
```
