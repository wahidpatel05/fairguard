# FairGuard SDK

Python SDK for integrating FairGuard into your ML pipeline.

## Installation

```bash
pip install fairguard-sdk
```

## Quick Start

### Audit a model batch

```python
import asyncio
import pandas as pd
from fairguard_sdk import FairGuardClient

async def main():
    async with FairGuardClient(
        api_url="http://localhost:8000/api/v1",
        api_key="fg_your_api_key"
    ) as client:
        df = pd.read_csv("model_predictions.csv")
        result = await client.run_audit(
            project_id="your-project-id",
            data=df,
            target_col="actual_label",
            prediction_col="model_prediction",
            sensitive_cols=["gender", "race", "age_group"]
        )
        print(f"Verdict: {result.verdict}")
        for ev in result.contract_evaluations:
            status = "✓" if ev["passed"] else "✗"
            print(f"  {status} {ev['attribute']} {ev['metric']}: {ev['value']:.3f}")

asyncio.run(main())
```

### LLM Pipeline Integration Example

```python
# Monitor an LLM-based hiring assistant in real time
async def monitor_llm_hiring_pipeline():
    async with FairGuardClient(api_url=FAIRGUARD_URL, api_key=FAIRGUARD_KEY) as client:
        # After each batch of LLM decisions, ingest them
        decisions = [
            {
                "decision_id": "app-001",
                "sensitive_attributes": {"gender": "F", "age_group": "25-34"},
                "outcome": "1",  # 1 = hired, 0 = rejected
                "timestamp": "2024-01-15T10:00:00Z"
            }
        ]
        await client.ingest_decisions(
            project_id="hiring-project-id",
            decisions=decisions
        )

        # Check runtime status
        status = await client.get_runtime_status("hiring-project-id")
        if status.overall_status == "critical":
            # Trigger alert or pause the pipeline
            raise RuntimeError("Fairness critical — halting LLM pipeline")
```

### Synchronous Usage (non-async)

```python
from fairguard_sdk import FairGuardClient

# The SDK also provides a synchronous interface via the context manager
with FairGuardClient(
    api_url="http://localhost:8000/api/v1",
    api_key="fg_your_api_key"
) as client:
    # Send audit data
    result = client.send_audit_data(
        project_id="your-project-id",
        data_path="predictions.csv",
        target_column="label",
        prediction_column="score",
        sensitive_columns=["gender", "age"],
    )
    print(f"Verdict: {result.verdict}")
```

## API Reference

### `FairGuardClient`

#### Constructor

```python
FairGuardClient(api_url: str, api_key: str, timeout: float = 120.0)
```

#### Methods

| Method | Description |
|--------|-------------|
| `run_audit(project_id, data, target_col, prediction_col, sensitive_cols)` | Run offline audit from a DataFrame |
| `send_audit_data(project_id, data_path, target_column, prediction_column, sensitive_columns)` | Run offline audit from a CSV file path |
| `get_runtime_status(project_id, aggregation_key?)` | Get runtime monitoring status |
| `ingest_decisions(project_id, decisions)` | Ingest model decisions for real-time monitoring |
| `get_receipt(receipt_id)` | Fetch a fairness receipt |
| `verify_receipt(receipt_id)` | Verify a receipt's cryptographic signature |
| `get_metrics(project_id)` | Get latest audit metrics |

### Type Reference

#### `AuditResult`
```python
@dataclass
class AuditResult:
    audit_id: str
    project_id: str
    verdict: str           # "pass", "fail", or "pass_with_warnings"
    dataset_hash: str
    contract_evaluations: list[dict]
    recommendations: list[dict]
    receipt_id: str | None
```

#### `RuntimeStatus`
```python
@dataclass
class RuntimeStatus:
    project_id: str
    overall_status: str    # "healthy", "warning", "critical", "no_data"
    windows: dict[str, dict]
    aggregation_key: str | None
```

#### `Receipt`
```python
@dataclass
class Receipt:
    id: str
    audit_id: str
    verdict: str
    signature: str | None
    public_key: str | None
    created_at: str
```

#### `VerificationResult`
```python
@dataclass
class VerificationResult:
    valid: bool
    receipt_id: str
    verified_at: str
    reason: str | None
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `FAIRGUARD_API_URL` | Base URL of your FairGuard instance |
| `FAIRGUARD_API_KEY` | Your API key |

## License

Apache 2.0
