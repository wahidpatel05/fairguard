import apiClient from './client';
import type { RuntimeStatusResponse, SnapshotOut } from '../types';

export type { RuntimeStatusResponse, SnapshotOut };

export const getRuntimeStatus = async (
  projectId: string,
  aggregationKey?: string,
): Promise<RuntimeStatusResponse> => {
  const params: Record<string, string> = { project_id: projectId };
  if (aggregationKey) params.aggregation_key = aggregationKey;
  const { data } = await apiClient.get<RuntimeStatusResponse>('/runtime/status', { params });
  return data;
};

export const getRuntimeSnapshots = async (
  projectId: string,
  aggregationKey?: string,
  limit?: number,
): Promise<SnapshotOut[]> => {
  const params: Record<string, string | number> = { project_id: projectId };
  if (aggregationKey) params.aggregation_key = aggregationKey;
  if (limit) params.limit = limit;
  const { data } = await apiClient.get<SnapshotOut[]>('/runtime/snapshots', { params });
  return data;
};

