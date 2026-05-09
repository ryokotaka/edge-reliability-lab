# Tiny Model Multi-Seed Stress Test

## Scope

The v7 tiny model result used one deterministic synthetic sample. That was useful for
adding a trainable inference stage, but the held-out split had only 3 anomaly rows.

This v8 experiment repeats the same tiny model comparison across multiple synthetic
seeds so the result is less dependent on one lucky split.

## Method

1. Generate 30 minutes of 1 Hz synthetic sensor data for each seed.
2. Use the same dropout, jitter, noisy, and restart-gap rates as the default sample.
3. For each seed, split usable rows chronologically: 70% train, 30% test.
4. Compare:
   - statistical scorer
   - float tiny learned model
   - quantized tiny learned model
5. Aggregate true positives, false positives, false negatives, recall, and F1 across
   all held-out rows.

Default seeds:

```text
11, 23, 42, 71, 101, 133, 191
```

## Result

| Metric | Statistical scorer | Float tiny model | Quantized tiny model |
| --- | ---: | ---: | ---: |
| seeds | 7 | 7 | 7 |
| held-out rows | 3676 | 3676 | 3676 |
| held-out anomalies | 41 | 41 | 41 |
| true positives | 32 | 37 | 37 |
| false positives | 0 | 0 | 0 |
| false negatives | 9 | 4 | 4 |
| precision | 1.0000 | 1.0000 | 1.0000 |
| recall | 0.7805 | 0.9024 | 0.9024 |
| aggregate F1 | 0.8767 | 0.9487 | 0.9487 |
| mean seed F1 | 0.8849 | 0.9558 | 0.9558 |
| minimum seed F1 | 0.7273 | 0.8333 | 0.8333 |
| model state size | 48 bytes | 104 bytes | 42 bytes |

## Interpretation

Across the multi-seed synthetic stress test, the learned tiny model detected more
held-out noisy rows than the statistical scorer. The quantized learned model preserved
the float learned model's aggregate F1 while using a smaller model state.

This is still synthetic evidence. It strengthens the reproducibility story for the
trainable inference stage, but it should not be described as real-world robustness or
hardware performance until the same comparison runs on a constrained target device.
