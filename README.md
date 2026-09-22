# Edge Reliability Lab

[![CI](https://github.com/ryokotaka/edge-reliability-lab/actions/workflows/python.yml/badge.svg)](https://github.com/ryokotaka/edge-reliability-lab/actions/workflows/python.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Python testbed for sensor pipelines that need to keep collecting data when writes
fail and run anomaly detection with limited resources.

You can replay the same failures, compare a buffered pipeline with direct writes,
and measure how model choice and sampling affect detection. The experiments use
synthetic temperature, humidity, and pressure data and run locally with the Python
standard library.

In the write-failure experiment, a local buffer recovered **all 120 readings** that
direct writes lost. Other experiments compare that kind of reliability gain with
the cost of smaller models, fewer inference calls, and batched storage.

## What the experiments show

The comparisons show where each change helps and what it costs:

| Comparison | Result | What to take from it |
| --- | --- | --- |
| Direct writes vs. a local buffer | 120 lost rows → 0 in the simulated write-failure window | Buffering recovers that window; existing sensor dropout remains. |
| Statistical scorer vs. learned classifier | F1 0.8767 → 0.9487 across seven seeds | The learned model detects 37 of 41 held-out anomalies; the scorer detects 32. Both have zero false positives. |
| Float vs. quantized-like learned model | Same aggregate F1, 0.9487 | Rounding the parameters preserves detection quality on these splits. |
| Fixed vs. adaptive sampling | 15.42% fewer inference calls; recall 0.9231 → 0.7692 | Skipping quiet periods also skips some isolated anomalies. |
| One SQLite commit per row vs. batches of 100 | 1,800 commits → 18 | Less commit overhead; elapsed time depends on the machine and storage. |
| Threshold alerts vs. two-sample confirmation | 2 false alerts → 0; recall 1.0000 → 0.8333 | The filter suppresses brief spikes but detects a sustained anomaly one sample later. |

These are default synthetic experiments. The model comparison uses seven deterministic
seeds and a chronological 70/30 train/test split per seed, with 3,676 held-out rows in
total. The other rows use the default sample or, for alert filtering, a separate
120-row challenge stream. Full methods and tables are in the [experiment notes](#experiment-notes).

## Run it locally

Requires Python 3.9 or newer. No sensor, cloud account, or ML framework is needed.
Run the commands from the repository root:

```bash
git clone https://github.com/ryokotaka/edge-reliability-lab.git
cd edge-reliability-lab
python3 -m venv .venv
. .venv/bin/activate

python scripts/generate_synthetic_data.py
python scripts/run_tiny_model_experiment.py
```

The generator writes `data/sample.csv`: 1,800 timestamped rows representing 30 minutes
at 1 Hz. It generates the whole file immediately. The experiment prints its results
and saves `data/tiny_model_experiment/summary.json`.

On this default split, all three models detect all three test anomalies. That small
sample is why the next experiment repeats the comparison across seven seeds:

```bash
python scripts/run_tiny_model_stress_experiment.py
python scripts/run_resource_budget_experiment.py
```

<details>
<summary>Run the remaining experiments and build the dashboard</summary>

After the commands above:

```bash
python -m edge_agent.storage data/sample.csv data/readings.sqlite
python -m edge_agent.metrics data/readings.sqlite

python scripts/run_recovery_experiment.py
python scripts/run_inference_experiment.py
python scripts/run_model_artifact_experiment.py
python scripts/run_sampling_experiment.py
python scripts/run_batch_write_experiment.py
python scripts/run_stability_filter_experiment.py
python dashboard/app.py
```

Open `dashboard/index.html` in a browser. It is a static report built from the local
`data/*_experiment/summary.json` files; it does not need a server. Regenerate it after
rerunning an experiment.

</details>

To run the tests, install the only development dependency:

```bash
python -m pip install pytest
python -m pytest
```

The sample CSV is tracked and can be regenerated. Databases, experiment output folders,
the virtual environment, and generated dashboard HTML are ignored by Git.

## How it works

Most experiments read the same CSV and run separate comparisons. SQLite is used for
the storage and recovery experiments; inference reads the CSV directly. Each experiment
writes a JSON summary that the dashboard collects. The multi-seed test generates its
own inputs, and the resource-budget check reads that test's summary.

The statistical scorer flags large deviations in temperature, humidity, or pressure.
The learned model is a logistic classifier with four weights and a bias, trained on
normalized deviations in those three signals plus latency. Normalization comes from
normal training rows. Anomaly labels come from the synthetic data generator.

The quantized-like model rounds the normalizer and learned parameters to integers,
then still uses floating-point operations to calculate probabilities. A separate
[export experiment](experiments/model_artifact.md) saves it as JSON and checks that
reloading it produces the same predictions without retraining.

| Location | Contents |
| --- | --- |
| [`edge_agent/`](edge_agent/) | Storage, metrics, buffering, inference, model training, and comparison functions |
| [`scripts/`](scripts/) | Data generator and experiment entry points; use `--help` for options |
| [`tests/`](tests/) | Tests for the experiment components and dashboard |
| [`dashboard/`](dashboard/) | Static HTML report generator |
| [`experiments/`](experiments/) | Methods, recorded results, and interpretation |

## Measurement notes

<details>
<summary>Data splits, parameter-size estimates, and what the metrics measure</summary>

The learned model and statistical scorer use different features and calibration
procedures, so their comparison does not isolate the effect of learning alone.
All seven seeds come from the same generator; they do not test a new sensor or a new
environment.

`model_state_bytes` is an estimate based on assumed numeric widths, not Python memory
usage or a serialized model size. For example, the learned model's 42-byte estimate
counts normalization values, weights, and bias, but excludes scales, the threshold,
and runtime overhead. The older scorer's 6-byte estimate assumes one byte per parameter
even though its values exceed that range; see the [quantization note](experiments/inference_quantization.md).
The resource-budget gate uses these estimates, so passing it does not establish that
a model fits in 64 bytes of device memory.

The reliability metrics also have specific meanings: `uptime_ratio` is the fraction of
expected rows marked `ok`, and `p95_latency_ms` summarizes generated latency values.
Neither measures live service availability or device inference time. The recovery
experiment models an unavailable database write path while the JSONL buffer remains
writable; it does not test sudden power loss.

</details>

## Experiment notes

| Topic | Details |
| --- | --- |
| Learned model | [Single split](experiments/tiny_model.md), [seven-seed comparison](experiments/tiny_model_stress.md) |
| Model size and export | [Resource budget](experiments/resource_budget.md), [saved model artifact](experiments/model_artifact.md) |
| Storage and recovery | [Buffered recovery](experiments/baseline_vs_optimized.md), [batch writes](experiments/batch_writes.md) |
| Scoring and alerts | [Quantization](experiments/inference_quantization.md), [adaptive sampling](experiments/adaptive_sampling.md), [confirmation filter](experiments/stability_filter.md) |
| Project background | [Architecture](docs/architecture.md), [experiment log](docs/experiment_log.md), [dashboard](dashboard/README.md) |

## Next step

Run the same comparisons on a Raspberry Pi Zero 2 W with a BME280 sensor. That would
let me measure actual latency, memory use, and storage behavior, and check whether the
sampling and alert policies still make sense with real sensor noise.

## License

[MIT](LICENSE).
