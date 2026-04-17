"""Rolling window runtime metrics monitor."""
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RuntimeMonitor:
    """Ingests runtime decisions and computes rolling fairness metrics."""

    WINDOW_HOURS = {"1hr": 1, "24hr": 24, "rolling_n": 1}

    async def ingest_decision(
        self,
        project_id: uuid.UUID,
        endpoint_id: str,
        decision_data: dict,
        db: AsyncSession,
    ) -> None:
        """Persist a single runtime decision to the database."""
        from models.db import RuntimeDecision

        ts = decision_data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = datetime.now(timezone.utc)

        decision = RuntimeDecision(
            project_id=project_id,
            endpoint_id=endpoint_id,
            decision_id=decision_data["decision_id"],
            sensitive_attributes=decision_data["sensitive_attributes"],
            decision_outcome=decision_data["decision_outcome"],
            ground_truth=decision_data.get("ground_truth"),
            timestamp=ts,
        )
        db.add(decision)

    async def get_rolling_metrics(
        self,
        project_id: uuid.UUID,
        endpoint_id: str,
        window: str,
        db: AsyncSession,
    ) -> dict:
        """Compute fairness metrics from recent decisions in the specified window."""
        from models.db import RuntimeDecision

        hours = self.WINDOW_HOURS.get(window, 1)
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = await db.execute(
            select(RuntimeDecision).where(
                RuntimeDecision.project_id == project_id,
                RuntimeDecision.endpoint_id == endpoint_id,
                RuntimeDecision.timestamp >= since,
            )
        )
        decisions = result.scalars().all()

        if not decisions:
            return {"decision_count": 0, "groups": {}, "disparate_impact": None, "message": "No data in window"}

        group_outcomes: dict[str, list[bool]] = {}
        for d in decisions:
            for attr, value in d.sensitive_attributes.items():
                key = f"{attr}={value}"
                group_outcomes.setdefault(key, []).append(d.decision_outcome)

        group_stats = {}
        positive_rates = []
        for grp, outcomes in group_outcomes.items():
            rate = sum(outcomes) / len(outcomes)
            group_stats[grp] = {"n": len(outcomes), "positive_rate": rate}
            positive_rates.append(rate)

        di = (min(positive_rates) / max(positive_rates)) if positive_rates and max(positive_rates) > 0 else 1.0

        return {
            "decision_count": len(decisions),
            "window": window,
            "groups": group_stats,
            "disparate_impact": round(di, 4),
        }

    def evaluate_status(self, metrics: dict, contracts: Optional[list[dict]] = None) -> str:
        """
        Evaluate runtime status as healthy/warning/critical.

        Without contracts, uses heuristics on disparate_impact.
        """
        di = metrics.get("disparate_impact")
        if di is None:
            return "healthy"

        if contracts:
            fails = 0
            for rule in contracts:
                if rule.get("metric") == "disparate_impact":
                    threshold = float(rule.get("threshold", 0.8))
                    if di < threshold:
                        fails += 1
            if fails > 0:
                return "critical"
            return "healthy"

        if di >= 0.8:
            return "healthy"
        elif di >= 0.6:
            return "warning"
        return "critical"

    async def save_metrics_snapshot(
        self,
        project_id: uuid.UUID,
        endpoint_id: str,
        window: str,
        metrics: dict,
        status: str,
        db: AsyncSession,
    ) -> None:
        """Persist a computed metrics snapshot to RuntimeMetrics table."""
        from models.db import RuntimeMetrics

        snapshot = RuntimeMetrics(
            project_id=project_id,
            endpoint_id=endpoint_id,
            window_type=window,
            metrics_json=metrics,
            status=status,
        )
        db.add(snapshot)


runtime_monitor = RuntimeMonitor()
