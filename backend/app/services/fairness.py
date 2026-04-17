"""FairnessEngine: core fairness computation using fairlearn and scikit-learn."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix
from fairlearn.metrics import (
    MetricFrame,
    selection_rate,
    true_positive_rate,
    false_positive_rate,
)


class FairnessEngine:
    """Compute per-attribute fairness metrics over a labelled prediction dataset."""

    @staticmethod
    def compute_metrics(
        df: pd.DataFrame,
        target_col: str,
        prediction_col: str,
        sensitive_cols: list[str],
    ) -> dict:
        """Compute fairness metrics for each sensitive attribute.

        Args:
            df: DataFrame containing predictions and ground-truth labels.
            target_col: Column name for the ground-truth binary label (0/1).
            prediction_col: Column name for the model prediction (0/1).
            sensitive_cols: List of column names for sensitive attributes.

        Returns:
            dict with keys ``"global"`` and ``"by_attribute"``.

        Raises:
            ValueError: If any required column is missing from *df*.
        """
        # 1. Validate columns
        required = [target_col, prediction_col] + sensitive_cols
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Columns not found in DataFrame: {missing}")

        # 2. Keep only the relevant columns
        df = df[[target_col, prediction_col] + sensitive_cols].copy()

        # 3. Drop rows with nulls in key columns
        df.dropna(subset=[target_col, prediction_col] + sensitive_cols, inplace=True)

        # 4. Convert target and prediction to int
        df[target_col] = df[target_col].astype(int)
        df[prediction_col] = df[prediction_col].astype(int)

        y_true = df[target_col]
        y_pred = df[prediction_col]

        # Global metrics
        total_rows = len(df)
        positive_outcome_rate = float((y_pred == 1).mean()) if total_rows > 0 else 0.0
        overall_accuracy = float(accuracy_score(y_true, y_pred)) if total_rows > 0 else 0.0

        by_attribute: dict[str, dict] = {}

        for sensitive_col in sensitive_cols:
            sensitive_feature = df[sensitive_col].astype(str)

            # 5a. Identify reference group (most frequent)
            value_counts = sensitive_feature.value_counts()
            reference_group = str(value_counts.idxmax())

            # 5b–5e. Build MetricFrame
            def _selection_rate(y_true: pd.Series, y_pred: pd.Series) -> float:  # noqa: ANN001
                return float((y_pred == 1).mean())

            metrics_dict = {
                "selection_rate": _selection_rate,
                "true_positive_rate": true_positive_rate,
                "false_positive_rate": false_positive_rate,
                "accuracy": accuracy_score,
            }

            mf = MetricFrame(
                metrics=metrics_dict,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_feature,
            )

            by_group: pd.DataFrame = mf.by_group
            overall = mf.overall

            # 5g. Cross-group disparities
            sr_values = by_group["selection_rate"]
            max_sr = float(sr_values.max())
            min_sr = float(sr_values.min())
            disparate_impact = (min_sr / max_sr) if max_sr > 0 else 0.0

            tpr_values = by_group["true_positive_rate"]
            tpr_difference = float(tpr_values.max() - tpr_values.min())

            fpr_values = by_group["false_positive_rate"]
            fpr_difference = float(fpr_values.max() - fpr_values.min())

            acc_values = by_group["accuracy"]
            accuracy_difference = float(acc_values.max() - acc_values.min())

            # 5h–5i. Per-group dict with plain-language explanations
            per_group: dict[str, dict] = {}
            for group_val in by_group.index:
                row = by_group.loc[group_val]
                group_sr = float(row["selection_rate"])
                group_tpr = float(row["true_positive_rate"])
                group_fpr = float(row["false_positive_rate"])
                group_acc = float(row["accuracy"])
                count = int((sensitive_feature == str(group_val)).sum())

                explanation = FairnessEngine._explain_group(
                    sensitive_col=sensitive_col,
                    group_val=str(group_val),
                    reference_group=reference_group,
                    selection_rate=group_sr,
                    tpr=group_tpr,
                    fpr=group_fpr,
                    accuracy=group_acc,
                    disparate_impact=disparate_impact,
                )

                per_group[str(group_val)] = {
                    "count": count,
                    "selection_rate": group_sr,
                    "tpr": group_tpr,
                    "fpr": group_fpr,
                    "accuracy": group_acc,
                    "explanation": explanation,
                }

            by_attribute[sensitive_col] = {
                "reference_group": reference_group,
                "disparate_impact": float(disparate_impact),
                "tpr_difference": tpr_difference,
                "fpr_difference": fpr_difference,
                "accuracy_difference": accuracy_difference,
                "overall": {
                    "selection_rate": float(overall["selection_rate"]),
                    "tpr": float(overall["true_positive_rate"]),
                    "fpr": float(overall["false_positive_rate"]),
                    "accuracy": float(overall["accuracy"]),
                },
                "per_group": per_group,
            }

        return {
            "global": {
                "total_rows": total_rows,
                "positive_outcome_rate": positive_outcome_rate,
                "overall_accuracy": overall_accuracy,
            },
            "by_attribute": by_attribute,
        }

    # ------------------------------------------------------------------
    # Contract evaluation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_contracts(metrics: dict, contracts_json: dict) -> list[dict]:
        """Evaluate contract rules against computed fairness metrics.

        Args:
            metrics: Output of :meth:`compute_metrics` (keys ``global`` and
                ``by_attribute``).
            contracts_json: Contract JSON blob, e.g. ``{"rules": [...]}``.

        Returns:
            List of evaluation result dicts compatible with
            :class:`~app.schemas.audit.ContractEvaluationResult`.
        """
        from services.fairness import evaluate_contracts as _eval  # legacy helper

        rules: list[dict] = contracts_json.get("rules", [])

        # Build flat metrics suitable for the legacy helper
        flat_metrics: dict = {}
        for attr, attr_data in metrics.get("by_attribute", {}).items():
            flat_metrics[attr] = {
                "disparate_impact": attr_data.get("disparate_impact", 0.0),
                "tpr_gap": attr_data.get("tpr_difference", 0.0),
                "tpr_difference": attr_data.get("tpr_difference", 0.0),
                "fpr_gap": attr_data.get("fpr_difference", 0.0),
                "accuracy_gap": attr_data.get("accuracy_difference", 0.0),
            }

        raw_results = _eval(flat_metrics, rules)

        # Build a quick look-up from contract_id → rule so we can enrich output
        rule_map: dict[str, dict] = {str(r.get("id", "")): r for r in rules}

        enriched: list[dict] = []
        for res in raw_results:
            rule = rule_map.get(res["contract_id"], {})
            enriched.append(
                {
                    "contract_id": res["contract_id"],
                    "attribute": rule.get("sensitive_column"),
                    "metric": res["metric"],
                    "value": res["value"],
                    "threshold": res["threshold"],
                    "operator": res["operator"],
                    "passed": res["status"] == "pass",
                    "severity": rule.get("severity"),
                    "explanation": res["explanation"],
                }
            )

        return enriched

    @staticmethod
    def compute_verdict(contract_results: list[dict]) -> str:
        """Determine overall audit verdict from contract evaluation results.

        Returns:
            ``"pass"``, ``"fail"``, or ``"pass_with_warnings"``.
        """
        if not contract_results:
            return "pass"
        statuses = {r.get("status", "pass" if r.get("passed") else "fail") for r in contract_results}
        if "fail" in statuses:
            return "fail"
        if "warn" in statuses:
            return "pass_with_warnings"
        # If all passed is True and no status "fail"/"warn", derive from 'passed'
        if any(not r.get("passed", True) for r in contract_results):
            return "fail"
        return "pass"

    @staticmethod
    def generate_mitigation_recommendations(
        failing_results: list[dict],
    ) -> list[dict]:
        """Generate mitigation recommendations for failing contract results.

        Args:
            failing_results: List of contract evaluation dicts where
                ``passed`` is ``False`` (or ``status`` is ``"fail"``).

        Returns:
            List of recommendation dicts with keys ``contract_id``,
            ``metric``, ``attribute``, and ``recommendations``.
        """
        _RECS: dict[str, list[str]] = {
            "disparate_impact": [
                "Reweight or resample training data to improve representation of underrepresented groups.",
                "Apply adversarial debiasing or fair representation learning techniques.",
                "Review feature selection to eliminate proxies for protected attributes.",
                "Consider pre-processing techniques such as Reweighing (AIF360).",
            ],
            "tpr_gap": [
                "Apply threshold optimization per group to equalize true positive rates.",
                "Use equalized odds post-processing (e.g., ThresholdOptimizer in fairlearn).",
                "Investigate data quality and labelling disparities across groups.",
            ],
            "tpr_difference": [
                "Apply threshold optimization per group to equalize true positive rates.",
                "Use equalized odds post-processing (e.g., ThresholdOptimizer in fairlearn).",
                "Investigate data quality and labelling disparities across groups.",
            ],
            "fpr_gap": [
                "Apply calibrated equalized odds post-processing.",
                "Review decision thresholds independently per group to balance false positive rates.",
            ],
            "accuracy_gap": [
                "Ensure balanced training samples across all demographic groups.",
                "Consider group-specific calibration or boosting strategies.",
                "Collect additional labelled data for underrepresented groups.",
            ],
        }
        _DEFAULT = [
            "Consult a fairness expert to review model behaviour for this metric.",
            "Consider auditing training data for systematic biases.",
        ]

        recommendations: list[dict] = []
        for result in failing_results:
            metric = result.get("metric", "")
            recs = _RECS.get(metric, _DEFAULT)
            recommendations.append(
                {
                    "contract_id": result.get("contract_id"),
                    "metric": metric,
                    "attribute": result.get("attribute"),
                    "value": result.get("value"),
                    "threshold": result.get("threshold"),
                    "recommendations": recs,
                }
            )
        return recommendations

    @staticmethod
    def _explain_group(
        sensitive_col: str,
        group_val: str,
        reference_group: str,
        selection_rate: float,
        tpr: float,
        fpr: float,
        accuracy: float,
        disparate_impact: float,
    ) -> str:
        """Generate a plain-language explanation for a single group's metrics."""
        is_reference = group_val == reference_group
        ref_note = " (reference group)" if is_reference else ""
        di_note = (
            f" The overall disparate impact ratio is {disparate_impact:.3f}"
            f" ({'≥0.8, within acceptable range' if disparate_impact >= 0.8 else '<0.8, potential adverse impact'})."
        )
        return (
            f"Group '{group_val}' on attribute '{sensitive_col}'{ref_note}: "
            f"selection rate = {selection_rate:.1%}, "
            f"true positive rate = {tpr:.1%}, "
            f"false positive rate = {fpr:.1%}, "
            f"accuracy = {accuracy:.1%}."
            f"{di_note}"
        )
