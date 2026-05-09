from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


MODEL_LABELS = {
    "statistical_scorer": "statistical scorer",
    "learned_float_like": "float tiny model",
    "learned_quantized_like": "quantized tiny model",
}


@dataclass(frozen=True)
class ResourceBudget:
    max_model_state_bytes: int = 64
    min_f1: float = 0.90
    max_false_negative_rate: float = 0.10
    max_false_positive_count: int = 0


@dataclass(frozen=True)
class BudgetResult:
    model_key: str
    label: str
    model_state_bytes: int
    f1: float
    false_negative: int
    true_anomaly_count: int
    false_negative_rate: float
    false_positive: int
    passes_state_budget: bool
    passes_f1_budget: bool
    passes_false_negative_budget: bool
    passes_false_positive_budget: bool
    passes_all: bool
    fail_reasons: list[str]


def evaluate_model_budget(
    model_key: str,
    metrics: Mapping[str, Any],
    budget: ResourceBudget,
) -> BudgetResult:
    model_state_bytes = int(metrics["model_state_bytes"])
    f1 = float(metrics["f1"])
    false_negative = int(metrics["false_negative"])
    true_anomaly_count = int(metrics["true_anomaly_count"])
    false_positive = int(metrics["false_positive"])
    false_negative_rate = (
        false_negative / true_anomaly_count
        if true_anomaly_count
        else 0.0
    )

    passes_state_budget = model_state_bytes <= budget.max_model_state_bytes
    passes_f1_budget = f1 >= budget.min_f1
    passes_false_negative_budget = false_negative_rate <= budget.max_false_negative_rate
    passes_false_positive_budget = false_positive <= budget.max_false_positive_count
    fail_reasons = []
    if not passes_state_budget:
        fail_reasons.append("model_state_bytes")
    if not passes_f1_budget:
        fail_reasons.append("f1")
    if not passes_false_negative_budget:
        fail_reasons.append("false_negative_rate")
    if not passes_false_positive_budget:
        fail_reasons.append("false_positive")

    return BudgetResult(
        model_key=model_key,
        label=MODEL_LABELS.get(model_key, model_key),
        model_state_bytes=model_state_bytes,
        f1=f1,
        false_negative=false_negative,
        true_anomaly_count=true_anomaly_count,
        false_negative_rate=false_negative_rate,
        false_positive=false_positive,
        passes_state_budget=passes_state_budget,
        passes_f1_budget=passes_f1_budget,
        passes_false_negative_budget=passes_false_negative_budget,
        passes_false_positive_budget=passes_false_positive_budget,
        passes_all=not fail_reasons,
        fail_reasons=fail_reasons,
    )


def choose_recommended_model(results: Mapping[str, BudgetResult]) -> str | None:
    passing = [result for result in results.values() if result.passes_all]
    if not passing:
        return None
    best = sorted(
        passing,
        key=lambda result: (
            result.model_state_bytes,
            -result.f1,
            result.false_negative_rate,
            result.model_key,
        ),
    )[0]
    return best.model_key


def run_resource_budget_comparison(
    stress_summary: Mapping[str, Any],
    *,
    budget: ResourceBudget = ResourceBudget(),
) -> dict[str, Any]:
    aggregate = stress_summary["aggregate"]
    results = {
        model_key: evaluate_model_budget(model_key, aggregate[model_key], budget)
        for model_key in MODEL_LABELS
    }
    recommended_model = choose_recommended_model(results)

    return {
        "source_summary": "data/tiny_model_stress_experiment/summary.json",
        "budget": asdict(budget),
        "seed_count": stress_summary["seed_count"],
        "total_test_anomaly_count": stress_summary["total_test_anomaly_count"],
        "models": {
            model_key: asdict(result)
            for model_key, result in results.items()
        },
        "recommended_model": recommended_model,
        "recommended_label": (
            MODEL_LABELS[recommended_model]
            if recommended_model is not None
            else None
        ),
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate tiny-model results against a small edge-style resource budget."
    )
    parser.add_argument(
        "--stress-summary",
        type=Path,
        default=Path("data/tiny_model_stress_experiment/summary.json"),
    )
    parser.add_argument("--max-model-state-bytes", type=int, default=64)
    parser.add_argument("--min-f1", type=float, default=0.90)
    parser.add_argument("--max-false-negative-rate", type=float, default=0.10)
    parser.add_argument("--max-false-positive-count", type=int, default=0)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    budget = ResourceBudget(
        max_model_state_bytes=args.max_model_state_bytes,
        min_f1=args.min_f1,
        max_false_negative_rate=args.max_false_negative_rate,
        max_false_positive_count=args.max_false_positive_count,
    )
    result = run_resource_budget_comparison(load_json(args.stress_summary), budget=budget)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
