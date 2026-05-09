# Resource Budget Gate

## Scope

This experiment converts the v8 multi-seed tiny-model results into a small edge-style
budget check.

It is not hardware measurement. It does not claim real RAM, CPU, latency, or power
usage. The goal is narrower: make the model-selection trade-off explicit before the
same pipeline moves to target hardware.

## Method

1. Load `data/tiny_model_stress_experiment/summary.json`.
2. Compare the statistical scorer, float tiny model, and quantized tiny model.
3. Apply the same proxy budget to each model.
4. Recommend the smallest model that passes all configured checks.

Default budget:

| Budget item | Threshold |
| --- | ---: |
| model state size | <= 64 bytes |
| aggregate F1 | >= 0.9000 |
| false-negative rate | <= 10.00% |
| false positives | <= 0 |

## Result

| Metric | Statistical scorer | Float tiny model | Quantized tiny model |
| --- | ---: | ---: | ---: |
| model state size | 48 bytes | 104 bytes | 42 bytes |
| aggregate F1 | 0.8767 | 0.9487 | 0.9487 |
| false-negative rate | 21.95% | 9.76% | 9.76% |
| false positives | 0 | 0 | 0 |
| state budget | pass | fail | pass |
| F1 budget | fail | pass | pass |
| false-negative budget | fail | pass | pass |
| false-positive budget | pass | pass | pass |
| all budgets | fail | fail | pass |

Recommended model under this proxy budget:

```text
quantized tiny model
```

## Interpretation

The statistical scorer has a small state, but it does not meet the default quality
thresholds on the multi-seed stress test. The float tiny model meets the quality
thresholds, but its stored state is above the default 64-byte budget. The quantized
tiny model is the only candidate that passes both the quality and state-size checks.

This makes the edge-oriented trade-off explicit, while keeping the limitation clear:
the budget gate is a proxy decision rule, not target-device measurement.
