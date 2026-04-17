export type Verdict = 'PASS' | 'FAIL' | 'PASS_WITH_WARNINGS';
export type RuntimeStatusLevel = 'healthy' | 'warning' | 'critical' | 'insufficient_data' | 'no_data';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// ── Auth ───────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

// ── Projects ───────────────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  domain: string;
  description?: string;
  owner_id: string;
  created_at: string;
}

export interface CreateProjectRequest {
  name: string;
  domain: string;
  description?: string;
}

// ── Contracts ──────────────────────────────────────────────────────────────

export interface ContractRule {
  id: string;
  metric: string;
  threshold: number;
  operator: 'gte' | 'lte';
  sensitive_column?: string | null;
  description?: string | null;
}

export interface ContractCreate {
  contracts: ContractRule[];
  notes?: string | null;
}

export interface ContractOut {
  id: string;
  project_id: string;
  version: number;
  is_current: boolean;
  contracts_json: { rules: ContractRule[] };
  created_by: string;
  created_at: string;
  notes: string | null;
}

// ── Audits ─────────────────────────────────────────────────────────────────

export interface AuditOut {
  id: string;
  project_id: string;
  contract_version_id: string | null;
  dataset_filename: string | null;
  dataset_hash: string | null;
  target_column: string | null;
  prediction_column: string | null;
  sensitive_columns: string[] | null;
  metrics_json: MetricsJson | null;
  verdict: string | null;
  triggered_by: string | null;
  user_id: string | null;
  created_at: string;
}

export interface AuditSummary {
  id: string;
  project_id: string;
  dataset_filename: string | null;
  dataset_hash: string | null;
  verdict: string | null;
  created_at: string;
}

export interface ContractEvaluationResult {
  contract_id: string;
  attribute: string | null;
  metric: string;
  value: number | null;
  threshold: number;
  operator: string;
  passed: boolean;
  severity: string | null;
  explanation: string;
}

export interface AuditResultResponse {
  audit: AuditOut;
  contract_evaluations: ContractEvaluationResult[];
  recommendations: Recommendation[];
  receipt_id: string | null;
}

export interface Recommendation {
  title?: string;
  description?: string;
  metric?: string;
  attribute?: string;
  [key: string]: unknown;
}

// ── Metrics JSON structure returned by FairnessEngine ─────────────────────

export interface PerGroupMetrics {
  count: number;
  selection_rate: number;
  tpr: number;
  fpr: number;
  accuracy: number;
  explanation: string;
}

export interface AttributeMetrics {
  reference_group: string;
  disparate_impact: number;
  tpr_difference: number;
  fpr_difference: number;
  accuracy_difference: number;
  overall: {
    selection_rate: number;
    tpr: number;
    fpr: number;
    accuracy: number;
  };
  per_group: Record<string, PerGroupMetrics>;
}

export interface GlobalMetrics {
  total_rows: number;
  positive_outcome_rate: number;
  overall_accuracy: number;
}

export interface MetricsJson {
  global: GlobalMetrics;
  by_attribute: Record<string, AttributeMetrics>;
}

// ── Runtime ────────────────────────────────────────────────────────────────

export interface RuntimeWindowStatus {
  metrics: Record<string, number>;
  status: string;
  evaluated_at: string | null;
  count: number;
}

export interface RuntimeStatusResponse {
  project_id: string;
  aggregation_key: string | null;
  windows: Record<string, RuntimeWindowStatus>;
  overall_status: string;
}

export interface SnapshotOut {
  id: string;
  project_id: string;
  aggregation_key: string | null;
  window_type: string;
  metrics_json: Record<string, unknown> | null;
  status: string;
  evaluated_at: string;
}

// ── Receipts ───────────────────────────────────────────────────────────────

export interface FairnessReceipt {
  id: string;
  project_id: string;
  audit_id?: string | null;
  verdict: string;
  payload: Record<string, unknown>;
  signature: string;
  created_at: string;
}

export interface VerifyResult {
  valid: boolean;
  message: string;
}

// ── API Keys ───────────────────────────────────────────────────────────────

export interface ApiKey {
  id: string;
  project_id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
}

// ── Helpers ────────────────────────────────────────────────────────────────

/** Chart-friendly group metric row extracted from audit results. */
export interface GroupMetric {
  group: string;
  approval_rate: number;
  tpr: number;
  fpr: number;
  accuracy: number;
}

/** Extract per-group metrics suitable for MetricsBarChart from audit metrics_json. */
export function extractGroupMetrics(
  metricsJson: MetricsJson | null,
): Array<{ group: string; approval_rate: number; tpr: number; fpr: number; accuracy: number }> {
  if (!metricsJson?.by_attribute) return [];
  const result: Array<{ group: string; approval_rate: number; tpr: number; fpr: number; accuracy: number }> = [];
  for (const [, attrData] of Object.entries(metricsJson.by_attribute)) {
    for (const [groupVal, groupData] of Object.entries(attrData.per_group)) {
      result.push({
        group: groupVal,
        approval_rate: groupData.selection_rate,
        tpr: groupData.tpr,
        fpr: groupData.fpr,
        accuracy: groupData.accuracy,
      });
    }
  }
  return result;
}

