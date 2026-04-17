import apiClient from './client';

export interface ContractResult {
  contract_id: string;
  metric: string;
  status: 'PASS' | 'FAIL' | 'WARNING';
  value: number;
  threshold: number;
  explanation: string;
}

export interface GroupMetric {
  group: string;
  approval_rate: number;
  tpr: number;
  fpr: number;
  accuracy: number;
}

export interface AuditResult {
  overall_verdict: 'PASS' | 'FAIL' | 'PASS_WITH_WARNINGS';
  contract_results: ContractResult[];
  group_metrics: GroupMetric[];
  receipt_id?: string;
}

export interface AuditLog {
  id: string;
  project_id: string;
  endpoint_id?: string;
  verdict: 'PASS' | 'FAIL' | 'PASS_WITH_WARNINGS';
  created_at: string;
  result?: AuditResult;
}

export const runAudit = async (formData: FormData): Promise<AuditResult> => {
  const { data } = await apiClient.post<AuditResult>('/audit/offline', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getAuditLogs = async (projectId?: string): Promise<AuditLog[]> => {
  const params = projectId ? { project_id: projectId } : {};
  const { data } = await apiClient.get<AuditLog[]>('/audit/logs', { params });
  return data;
};

export const getAuditDetail = async (id: string): Promise<AuditLog> => {
  const { data } = await apiClient.get<AuditLog>(`/audit/logs/${id}`);
  return data;
};
