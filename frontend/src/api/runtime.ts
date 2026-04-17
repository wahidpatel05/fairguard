import apiClient from './client';

export interface Decision {
  decision_id: string;
  endpoint_id: string;
  project_id: string;
  input_features: Record<string, unknown>;
  prediction: number | string;
  sensitive_attributes: Record<string, unknown>;
  timestamp?: string;
}

export interface RuntimeContractStatus {
  contract_id: string;
  metric: string;
  status: 'healthy' | 'warning' | 'critical';
  current_value: number;
  threshold: number;
}

export interface RuntimeStatus {
  project_id: string;
  endpoint_id?: string;
  overall_status: 'healthy' | 'warning' | 'critical';
  contract_statuses: RuntimeContractStatus[];
  last_updated: string;
}

export interface RuntimeHistoryPoint {
  timestamp: string;
  metric: string;
  value: number;
  group?: string;
}

export const ingestDecisions = async (data: Decision[]): Promise<void> => {
  await apiClient.post('/runtime/ingest', data);
};

export const getRuntimeStatus = async (
  projectId: string,
  endpointId?: string
): Promise<RuntimeStatus> => {
  const params: Record<string, string> = { project_id: projectId };
  if (endpointId) params.endpoint_id = endpointId;
  const { data } = await apiClient.get<RuntimeStatus>('/runtime/status', { params });
  return data;
};

export const getRuntimeHistory = async (
  projectId: string,
  endpointId?: string,
  window?: string
): Promise<RuntimeHistoryPoint[]> => {
  const params: Record<string, string> = { project_id: projectId };
  if (endpointId) params.endpoint_id = endpointId;
  if (window) params.window = window;
  const { data } = await apiClient.get<RuntimeHistoryPoint[]>('/runtime/history', { params });
  return data;
};
