# FairGuard Usage Guide

FairGuard is an AI Fairness Firewall that continuously monitors your ML models for
discriminatory patterns and enforces customisable fairness contracts.

---

## Table of Contents

1. [Setup and Installation](#1-setup-and-installation)
2. [Creating Projects and Contracts](#2-creating-projects-and-contracts)
3. [Running Audits](#3-running-audits)
4. [Interpreting Results](#4-interpreting-results)
5. [Runtime Monitoring](#5-runtime-monitoring)
6. [Understanding Fairness Metrics](#6-understanding-fairness-metrics)

---

## 1. Setup and Installation

### Prerequisites

- Python 3.10 or later
- A FairGuard account and API key

### Install the CLI

```bash
pip install fairguard-cli
```

### Install the Python SDK (optional)

```bash
pip install fairguard-sdk
```

### Configure credentials

Export your API key as an environment variable (never hard-code it):

```bash
export FAIRGUARD_API_KEY=fgk_your_api_key_here
```

Then run the interactive init wizard to create a project config file:

```bash
fairguard init
```

This creates `.fairguard.yml` in the current directory with your API URL and
Project ID. The API key is **not** written to disk.

```yaml
# .fairguard.yml
api_url: https://api.fairguard.io
project_id: proj_abc123
```

---

## 2. Creating Projects and Contracts

A **project** represents a single ML use case (e.g. "Loan Scoring Model").
A **fairness contract** defines which metrics to measure and what thresholds
are acceptable.

### Create a project via the API

```bash
curl -X POST https://api.fairguard.io/api/v1/projects \
  -H "Authorization: Bearer $FAIRGUARD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Loan Scoring Model",
    "description": "Production credit-scoring endpoint",
    "fairness_contract": {
      "metrics": ["demographic_parity", "equalized_odds"],
      "thresholds": {
        "demographic_parity": 0.1,
        "equalized_odds": 0.1
      }
    }
  }'
```

### Contract parameters

| Parameter | Description | Typical value |
| --------- | ----------- | ------------- |
| `metrics` | List of fairness metrics to evaluate | `["demographic_parity", "equalized_odds"]` |
| `thresholds` | Maximum allowed disparity per metric | `0.1` (10%) |

---

## 3. Running Audits

### Offline audit (batch)

An offline audit uploads a CSV file and evaluates fairness across the entire batch.
Your CSV must contain at minimum a ground-truth column, a prediction column, and
one or more sensitive-attribute columns.

**Example CSV (`predictions.csv`):**

```
id,label,score,gender,age_group
1,1,0.87,F,25-34
2,0,0.21,M,45-54
3,1,0.91,F,25-34
...
```

**Run the audit:**

```bash
fairguard test \
  --data predictions.csv \
  --target label \
  --prediction score \
  --sensitive gender,age_group
```

The command prints a results table and exits with code `0` (pass) or `1` (fail),
making it suitable as a CI gate.

### Offline audit via SDK

```python
import fairguard_sdk

fairguard_sdk.configure(
    api_url="https://api.fairguard.io",
    api_key="fgk_your_api_key_here",
)

result = fairguard_sdk.send_audit_data(
    project_id="proj_abc123",
    data_path="predictions.csv",
    target_column="label",
    prediction_column="score",
    sensitive_columns=["gender", "age_group"],
)

print(result.verdict)   # "PASS" or "FAIL"
print(result.metrics)
print(result.violations)
```

---

## 4. Interpreting Results

### Verdict

| Verdict | Meaning |
| ------- | ------- |
| `PASS` | All fairness metrics are within the configured thresholds. |
| `FAIL` | One or more metrics exceeded their threshold — action required. |

### Metrics table

Each metric entry reports:

- **Value** — the measured disparity (lower is fairer).
- **Threshold** — the maximum allowed disparity from your contract.
- **Status** — `PASS` or `FAIL` for this individual metric.

### Violations

Each violation entry names the specific metric and the sensitive-attribute group
that caused it, e.g.:

```
demographic_parity exceeded (0.23 > 0.10) for gender=F vs gender=M
```

### Generating a report

```bash
fairguard report --output fairguard-report.md
```

This fetches the latest audit result and writes a Markdown report you can share
with stakeholders or store as a CI artifact.

---

## 5. Runtime Monitoring

In addition to batch audits, FairGuard can monitor model decisions in real time.

### Ingesting decisions via SDK

```python
from fairguard_sdk import FairGuardClient

client = FairGuardClient(
    api_url="https://api.fairguard.io",
    api_key="fgk_your_api_key_here",
)

# Call this for every model prediction in your application.
client.ingest_decisions(
    project_id="proj_abc123",
    decisions=[
        {
            "decision_id": "d_001",
            "prediction": 1,
            "score": 0.87,
            "ground_truth": None,  # may be unknown at inference time
            "attributes": {"gender": "F", "age_group": "25-34"},
            "timestamp": "2024-01-15T12:00:00Z",
        }
    ],
)
```

### Checking runtime status

```bash
fairguard status
```

Or via SDK:

```python
status = client.get_runtime_status(project_id="proj_abc123")
print(status["status"])          # "OK" or "DEGRADED"
print(status["endpoints"])       # per-endpoint breakdown
```

### Alerts

Configure alert webhooks in the FairGuard dashboard to receive Slack, PagerDuty, or
email notifications when a fairness threshold is breached at runtime.

---

## 6. Understanding Fairness Metrics

FairGuard measures several complementary notions of fairness. You don't need a
statistics background to use them — this section explains each metric in plain
language.

### Demographic Parity (Statistical Parity)

**Plain language:** "Are positive outcomes granted at similar rates across groups?"

A loan model satisfies demographic parity if it approves roughly the same
*proportion* of female applicants as male applicants — regardless of whether those
individual decisions are correct.

**Measured as:** |P(ŷ=1 | A=0) − P(ŷ=1 | A=1)|
**Passes when:** value ≤ threshold (e.g. ≤ 0.10)

---

### Equalized Odds

**Plain language:** "Do errors affect all groups equally?"

A model satisfies equalized odds if it has similar *true positive rates* and
*false positive rates* across groups. This means both "catching real positives"
and "accidentally flagging negatives" happen at the same frequency for everyone.

**Measured as:** max(|TPR₀ − TPR₁|, |FPR₀ − FPR₁|)
**Passes when:** value ≤ threshold

---

### Equal Opportunity

**Plain language:** "Are qualified individuals in all groups identified at the same rate?"

A relaxed version of equalized odds that only checks the true positive rate (recall).
Useful when false negatives (missing a qualified candidate) are the primary concern.

**Measured as:** |TPR₀ − TPR₁|
**Passes when:** value ≤ threshold

---

### Predictive Parity (Calibration)

**Plain language:** "Does a positive prediction mean the same thing for everyone?"

A model satisfies predictive parity if, among all applicants predicted to receive
a positive outcome, the proportion who truly deserve it is similar across groups.
High predictive parity means the model's confidence is equally well-calibrated for
all groups.

**Measured as:** |P(y=1 | ŷ=1, A=0) − P(y=1 | ŷ=1, A=1)|
**Passes when:** value ≤ threshold

---

### Choosing the right metric

There is no single "best" fairness metric — the right choice depends on the harm
you are most concerned about:

| Primary concern | Recommended metric |
| --------------- | ------------------ |
| Unequal access to opportunities | Demographic Parity |
| Errors disproportionately harming a group | Equalized Odds |
| Missing qualified individuals from a group | Equal Opportunity |
| Model confidence varying by group | Predictive Parity |

FairGuard lets you enforce multiple metrics simultaneously via your fairness contract.
It is common to enforce all four with a threshold of 0.10 as a starting point, then
tighten thresholds over time.

---

## Further Reading

- [API Reference](./api-reference.md)
- [CI/CD Integration Examples](./ci-examples.md)
- [FairGuard GitHub Repository](https://github.com/fairguard/fairguard)
