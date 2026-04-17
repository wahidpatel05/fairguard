# FairGuard API Reference

Base URL: `https://api.fairguard.io` (self-hosted: configured via `FAIRGUARD_API_URL`)

All endpoints require `Authorization: Bearer <api_key>` unless noted.

---

## Authentication

```
Authorization: Bearer fgk_your_api_key_here
```

---

## Audit Endpoints

### POST /api/v1/audit/offline

Run an offline fairness audit by uploading a CSV file.

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `file` | file | ✔ | CSV file with predictions |
| `project_id` | string | ✔ | Project identifier |
| `target_column` | string | ✔ | Ground-truth label column name |
| `prediction_column` | string | ✔ | Model prediction/score column name |
| `sensitive_columns` | string | ✔ | Comma-separated sensitive attribute columns |
| `endpoint_id` | string | | Optional endpoint scope |

**Response 200:**

```json
{
  "audit_id": "aud_01HXYZ",
  "project_id": "proj_abc123",
  "verdict": "PASS",
  "metrics": {
    "demographic_parity": {
      "value": 0.04,
      "threshold": 0.1,
      "status": "PASS"
    },
    "equalized_odds": {
      "value": 0.07,
      "threshold": 0.1,
      "status": "PASS"
    },
    "predictive_parity": {
      "value": 0.05,
      "threshold": 0.1,
      "status": "PASS"
    }
  },
  "violations": [],
  "receipt_id": "rec_01HXYZ",
  "created_at": "2024-01-15T12:00:00Z"
}
```

**Response 422 — validation error:**

```json
{
  "detail": "Column 'gender' not found in uploaded CSV."
}
```

---

### GET /api/v1/audit/{audit_id}

Retrieve a specific audit result.

**Path Parameters:**

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| `audit_id` | string | Audit identifier |

**Response 200:** Same schema as POST /api/v1/audit/offline response.

---

### GET /api/v1/projects/{project_id}/audits/latest

Get the most recent audit for a project.

**Response 200:** Same schema as audit result.

---

## Metrics Endpoints

### GET /api/v1/projects/{project_id}/metrics

Get the latest aggregated fairness metrics for a project.

**Query Parameters:**

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| `endpoint_id` | string | (optional) Filter to a specific endpoint |

**Response 200:**

```json
{
  "project_id": "proj_abc123",
  "period": "last_7_days",
  "metrics": {
    "demographic_parity": {
      "value": 0.04,
      "trend": "stable",
      "threshold": 0.1,
      "status": "PASS"
    },
    "equalized_odds": {
      "value": 0.07,
      "trend": "improving",
      "threshold": 0.1,
      "status": "PASS"
    }
  },
  "total_decisions": 150000
}
```

---

## Status Endpoints

### GET /api/v1/projects/{project_id}/status

Get real-time monitoring status.

**Query Parameters:**

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| `endpoint_id` | string | (optional) Scope to a single endpoint |

**Response 200:**

```json
{
  "project_id": "proj_abc123",
  "status": "OK",
  "endpoints": [
    {
      "endpoint_id": "ep_01",
      "name": "loan-scoring-prod",
      "status": "OK",
      "requests_24h": 4821,
      "violations_24h": 2
    }
  ],
  "last_updated": "2024-01-15T12:05:00Z"
}
```

---

## Decision Ingestion

### POST /api/v1/decisions/ingest

Ingest a batch of model decisions for real-time fairness monitoring.

**Request Body (JSON):**

```json
{
  "project_id": "proj_abc123",
  "decisions": [
    {
      "decision_id": "d_001",
      "prediction": 1,
      "score": 0.87,
      "ground_truth": 1,
      "attributes": {
        "gender": "F",
        "age_group": "25-34"
      },
      "timestamp": "2024-01-15T12:00:00Z"
    }
  ]
}
```

**Response 200:**

```json
{
  "ingested_count": 1,
  "receipt_id": "rec_01HABC",
  "project_id": "proj_abc123"
}
```

---

## Receipts

### GET /api/v1/receipts/{receipt_id}

Fetch a cryptographic audit receipt.

**Response 200:**

```json
{
  "receipt_id": "rec_01HXYZ",
  "audit_id": "aud_01HXYZ",
  "project_id": "proj_abc123",
  "verdict": "PASS",
  "data_hash": "sha256:abc123...",
  "signature": "base64-encoded-signature",
  "public_key_id": "key_01",
  "issued_at": "2024-01-15T12:00:00Z"
}
```

### POST /api/v1/receipts/{receipt_id}/verify

Verify the cryptographic integrity of a receipt.

**Response 200:**

```json
{
  "receipt_id": "rec_01HXYZ",
  "valid": true,
  "verified_at": "2024-01-15T12:10:00Z"
}
```

---

## Projects

### POST /api/v1/projects

Create a new project.

**Request Body (JSON):**

```json
{
  "name": "Loan Scoring Model",
  "description": "Production credit-scoring endpoint",
  "fairness_contract": {
    "metrics": ["demographic_parity", "equalized_odds"],
    "thresholds": {
      "demographic_parity": 0.1,
      "equalized_odds": 0.1
    }
  }
}
```

**Response 201:**

```json
{
  "project_id": "proj_abc123",
  "name": "Loan Scoring Model",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### GET /api/v1/projects/{project_id}

Get project details.

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
| ------ | ------- |
| 400 | Bad request — invalid parameters |
| 401 | Unauthorized — missing or invalid API key |
| 403 | Forbidden — insufficient permissions |
| 404 | Not found |
| 422 | Unprocessable entity — validation failed |
| 429 | Rate limited |
| 500 | Internal server error |
