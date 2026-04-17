"""Fairness metric computation (manual numpy/pandas implementation with optional fairlearn)."""
import hashlib
import io
from typing import Optional
import numpy as np
import pandas as pd


VALID_METRICS = {
    "disparate_impact",
    "tpr_gap",
    "tpr_difference",
    "fpr_gap",
    "accuracy_gap",
}


def compute_dataset_hash(df: pd.DataFrame) -> str:
    """Compute a SHA-256 hash of the DataFrame's CSV bytes."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def _group_positive_rates(y_true, y_pred, groups):
    """Compute per-group positive prediction rates and error rates."""
    results = {}
    unique_groups = np.unique(groups)
    for grp in unique_groups:
        mask = groups == grp
        y_t = y_true[mask]
        y_p = y_pred[mask]
        n = mask.sum()
        if n == 0:
            continue
        pos_pred_rate = y_p.mean()
        tp = ((y_t == 1) & (y_p == 1)).sum()
        fn = ((y_t == 1) & (y_p == 0)).sum()
        fp = ((y_t == 0) & (y_p == 1)).sum()
        tn = ((y_t == 0) & (y_p == 0)).sum()
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        accuracy = (tp + tn) / n
        results[str(grp)] = {
            "n": int(n),
            "positive_rate": float(pos_pred_rate),
            "tpr": float(tpr),
            "fpr": float(fpr),
            "accuracy": float(accuracy),
        }
    return results


def compute_fairness_metrics(
    df: pd.DataFrame,
    target_column: str,
    prediction_column: str,
    sensitive_columns: list[str],
) -> dict:
    """
    Compute fairness metrics for each sensitive attribute column.

    Returns a nested dict: { sensitive_column -> { metric_name -> value, groups -> {...} } }
    """
    y_true = df[target_column].astype(int).values
    y_pred = df[prediction_column].astype(int).values
    metrics_by_attribute = {}

    for col in sensitive_columns:
        groups = df[col].astype(str).values
        group_stats = _group_positive_rates(y_true, y_pred, groups)

        positive_rates = [v["positive_rate"] for v in group_stats.values()]
        tprs = [v["tpr"] for v in group_stats.values()]
        fprs = [v["fpr"] for v in group_stats.values()]
        accuracies = [v["accuracy"] for v in group_stats.values()]

        di = (min(positive_rates) / max(positive_rates)) if max(positive_rates) > 0 else 1.0
        tpr_gap = float(max(tprs) - min(tprs)) if tprs else 0.0
        fpr_gap = float(max(fprs) - min(fprs)) if fprs else 0.0
        acc_gap = float(max(accuracies) - min(accuracies)) if accuracies else 0.0

        metrics_by_attribute[col] = {
            "disparate_impact": float(di),
            "tpr_gap": tpr_gap,
            "tpr_difference": tpr_gap,
            "fpr_gap": fpr_gap,
            "accuracy_gap": acc_gap,
            "groups": group_stats,
        }

    return metrics_by_attribute


def evaluate_contracts(metrics: dict, contracts: list[dict]) -> list[dict]:
    """
    Evaluate a list of contract rules against computed metrics.

    Each contract rule: { id, metric, threshold, operator, sensitive_column (optional) }
    Returns list of { contract_id, metric, value, threshold, operator, status, explanation }
    """
    results = []
    for rule in contracts:
        contract_id = rule.get("id", "unknown")
        metric_name = rule["metric"]
        threshold = float(rule["threshold"])
        operator = rule.get("operator", "gte")
        sensitive_column = rule.get("sensitive_column")

        value = None
        if sensitive_column and sensitive_column in metrics:
            value = metrics[sensitive_column].get(metric_name)
        else:
            candidates = [
                attr_metrics.get(metric_name)
                for attr_metrics in metrics.values()
                if isinstance(attr_metrics, dict) and metric_name in attr_metrics
            ]
            if candidates:
                # disparate_impact: take min (lower = more disparate = worst case)
                # gap metrics: take max (higher gap = more unfair = worst case)
                value = min(candidates) if metric_name == "disparate_impact" else max(candidates)

        if value is None:
            results.append({
                "contract_id": str(contract_id),
                "metric": metric_name,
                "value": None,
                "threshold": threshold,
                "operator": operator,
                "status": "warn",
                "explanation": f"Metric '{metric_name}' could not be computed.",
            })
            continue

        if operator == "gte":
            passed = value >= threshold
        else:  # lte
            passed = value <= threshold

        status = "pass" if passed else "fail"
        explanation = _explain_metric(metric_name, value, threshold, operator, passed)

        results.append({
            "contract_id": str(contract_id),
            "metric": metric_name,
            "value": float(value),
            "threshold": threshold,
            "operator": operator,
            "status": status,
            "explanation": explanation,
        })

    return results


def _explain_metric(metric: str, value: float, threshold: float, operator: str, passed: bool) -> str:
    """Generate a plain-language explanation of a metric result."""
    op_word = "at least" if operator == "gte" else "at most"
    status_word = "PASSED" if passed else "FAILED"
    explanations = {
        "disparate_impact": (
            f"Disparate Impact (DI) measures the ratio of positive outcome rates between groups. "
            f"DI = {value:.3f} (required {op_word} {threshold}). "
            f"A DI < 0.8 may indicate potential adverse impact. Contract {status_word}."
        ),
        "tpr_gap": (
            f"True Positive Rate gap across groups = {value:.3f} (required {op_word} {threshold}). "
            f"Larger values indicate unequal recall across groups. Contract {status_word}."
        ),
        "tpr_difference": (
            f"True Positive Rate difference = {value:.3f} (required {op_word} {threshold}). "
            f"Contract {status_word}."
        ),
        "fpr_gap": (
            f"False Positive Rate gap = {value:.3f} (required {op_word} {threshold}). "
            f"Larger values indicate unequal false alarm rates across groups. Contract {status_word}."
        ),
        "accuracy_gap": (
            f"Accuracy gap = {value:.3f} (required {op_word} {threshold}). "
            f"Measures disparity in model accuracy between groups. Contract {status_word}."
        ),
    }
    return explanations.get(
        metric,
        f"Metric '{metric}' = {value:.3f} (required {op_word} {threshold}). Contract {status_word}."
    )


def determine_overall_verdict(contract_statuses: list[dict]) -> str:
    """Determine overall audit verdict from individual contract results."""
    if not contract_statuses:
        return "pass"
    statuses = {r["status"] for r in contract_statuses}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "pass_with_warnings"
    return "pass"
