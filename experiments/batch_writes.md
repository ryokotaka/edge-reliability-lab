# Batch SQLite Write Experiment

## Scope

This experiment compares direct per-row SQLite writes against batched writes. It uses
the same `data/sample.csv` rows for both paths.

This is not yet a Raspberry Pi storage benchmark. The stable evidence is the reduction
in insert calls and commit count. Elapsed time should be re-measured on target hardware.

## Method

1. Load 1800 synthetic readings.
2. Baseline: write one row per `executemany` call and commit every row.
3. Optimized: write batches of 100 rows and commit every batch.
4. Compare insert calls, commit count, rows per commit, and elapsed write time.

## Result

| Metric | Direct per-row writes | Batched writes |
| --- | ---: | ---: |
| rows written | 1800 | 1800 |
| batch size | 1 | 100 |
| insert calls | 1800 | 18 |
| commit count | 1800 | 18 |
| rows per insert call | 1 | 100 |
| rows per commit | 1 | 100 |
| elapsed write time | ~5.5 s | ~67 ms |

## Interpretation

Batching reduced insert calls and commits by 1782 each. This matters for local edge
storage because each commit can add overhead and wear-sensitive writes on constrained
storage. The timing result is machine-dependent; the next step is to repeat this on
Raspberry Pi with the target microSD card and record wall-clock write time.
