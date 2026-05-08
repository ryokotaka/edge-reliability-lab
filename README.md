# Edge AI Reliability Benchmark

## Problem

AI inference systems often fail in ways that are hidden in clean benchmark settings:
sensor or simulation streams can be delayed, missing, noisy, or interrupted,
local storage can become a bottleneck, and lightweight inference can increase latency,
memory use, and recovery risk.

This project builds a small reproducible edge AI reliability benchmark to collect
sensor or simulation data, store it locally, run lightweight inference or anomaly
detection, measure reliability and inference cost, and compare software optimizations
under physical and resource-constrained conditions.

## What This System Does

This project is building a minimal edge AI reliability and optimization pipeline:

1. Generate or collect sensor-like data
2. Store readings locally in SQLite
3. Measure reliability metrics
4. Run lightweight anomaly detection
5. Apply software-level optimizations
6. Compare baseline vs optimized results
7. Explain results with reproducible logs and a dashboard

The current implementation covers synthetic data generation, SQLite storage,
reliability metrics, and a local buffer / checkpoint recovery experiment.
Lightweight inference, quantization, adaptive sampling, and the dashboard are not
implemented yet.

## Architecture

```text
synthetic sensor data
  -> collector / generator
  -> SQLite
  -> lightweight inference / anomaly detection
  -> metrics
  -> optimization
  -> dashboard
  -> experiment log
```

## Current Version

`v1` uses synthetic environmental sensor data instead of real hardware.
The goal is to make the reliability and recovery pipeline measurable before adding
Raspberry Pi hardware, lightweight inference, and later optimization experiments.

The base measurement flow is:

```text
synthetic sensor data
  -> CSV
  -> SQLite readings table
  -> reliability metrics
  -> README explanation
```

The first software optimization experiment is:

```text
synthetic sensor data
  -> simulated SQLite write failure
  -> baseline direct write loses rows
  -> optimized local JSONL buffer checkpoints rows
  -> recovered rows are flushed to SQLite
  -> baseline vs optimized recovery metrics
```

## Metrics

| Metric | Meaning |
| --- | --- |
| `missing_rate` | Fraction of expected samples that are missing |
| `p95_latency_ms` | 95th percentile of non-missing sample latency |
| `uptime_ratio` | Fraction of expected samples that are normal `ok` readings |
| `recovery_loss` | Expected sequence slots absent after a restart or write failure |
| `inference_latency_ms` | Time spent in lightweight anomaly detection |
| `memory_mb` | Approximate memory usage during inference |

The v0 implementation calculates `missing_rate`, `p95_latency_ms`, and
`uptime_ratio`. The v1 recovery experiment also calculates `recovery_loss`.
Inference and resource metrics are planned for later versions.

## Optimization Plan

The project does not stop at measurement. The final goal is to compare a baseline
pipeline against software-level optimizations.

| Problem | Optimization | Main Metrics |
| --- | --- | --- |
| missing samples or restart loss | local buffer / checkpoint | missing rate / recovery loss |
| storage latency | batch writes | p95 latency / write count |
| heavy inference | quantization / smaller model | inference latency / memory / accuracy drop |
| wasted work during normal periods | adaptive sampling | CPU / power / event detection quality |

The first planned optimization is local buffering and checkpoint recovery. The second
is quantized or smaller lightweight inference.

## Synthetic Data

The v0 simulator generates 30 minutes of 1 Hz sensor-like data with:

- temperature
- humidity
- pressure
- latency jitter
- synthetic dropout
- optional noisy readings
- optional restart-gap markers

The CSV schema is:

| Column | Type | Meaning |
| --- | --- | --- |
| `ts_utc` | text | Observation timestamp |
| `seq` | int | Expected sequence number |
| `source` | text | `synthetic` for v0 |
| `temperature_c` | float | Environmental temperature |
| `humidity_pct` | float | Environmental humidity |
| `pressure_hpa` | float | Environmental pressure |
| `latency_ms` | float | Acquisition latency |
| `status` | text | `ok`, `missing`, `noisy`, or `restart_gap` |
| `fault_type` | text | `none`, `dropout`, `noise`, or `restart` |

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest

python3 scripts/generate_synthetic_data.py
python3 -m edge_agent.storage data/sample.csv data/readings.sqlite
python3 -m edge_agent.metrics data/readings.sqlite
python3 scripts/run_recovery_experiment.py
python3 -m pytest
```

## Example Results

These values come from the default deterministic synthetic sample.

| Metric | Result | Note |
| --- | ---: | --- |
| expected samples | 1800 | 30 minutes at 1 Hz |
| absent samples | 0 | no lost sequence slots |
| missing rate | 0.0344 | synthetic dropout |
| p95 latency | 132.089 ms | non-missing rows |
| uptime ratio | 0.9539 | ok rows / expected rows |
| recovery loss | 0 | base sample has no simulated write failure |

## Baseline vs Optimized

The current recovery experiment simulates a SQLite write failure for sequence
`600..719`. Direct writes lose those rows; the optimized path stores them in a
local JSONL buffer with a checkpoint and flushes them after recovery.

| Metric | Baseline direct write | Buffered recovery | Change |
| --- | ---: | ---: | ---: |
| observed samples | 1680 | 1800 | +120 |
| missing rate | 0.0989 | 0.0344 | -0.0645 |
| p95 latency | 125.789 ms | 132.089 ms | +6.300 ms |
| uptime ratio | 0.8900 | 0.9539 | +0.0639 |
| recovery loss | 120 samples | 0 samples | -120 |
| recovered rows | 0 | 120 | +120 |

This result is intentionally narrow: local buffering reduces recovery loss, but it
does not make the underlying synthetic dropout disappear.

## Planned Hardware

The first hardware target is:

- Raspberry Pi Zero 2 W
- BME280 temperature / humidity / pressure sensor
- local SQLite storage
- optional USB power meter

The project intentionally starts without hardware to validate the pipeline first.
Hardware is added later to expose real constraints such as CPU, memory, I/O,
thermal behavior, and optional power usage.

## Limitations

- v0 uses synthetic data only
- no cloud backend
- no large ML model
- no camera input
- no Kubernetes or distributed system layer
- no custom circuit board design

The focus is software-level reliability and optimization under constrained edge-like
conditions.

## Future Work

- connect BME280 sensor
- add MPU-6050 motion sensor
- add Streamlit dashboard
- add anomaly detection with rolling z-score
- compare real sensor data with synthetic fault injection
- add local buffering and checkpoint recovery
- compare float32 vs quantized lightweight inference
- compare fixed sampling vs adaptive sampling
- add a short 90-second demo
