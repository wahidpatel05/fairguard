import apiClient from './client';
import type { AuditSummary, AuditResultResponse } from '../types';

export type { AuditSummary, AuditResultResponse };

export const runAudit = async (formData: FormData): Promise<AuditResultResponse> => {
  const { data } = await apiClient.post<AuditResultResponse>('/audit/offline', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getAuditLogs = async (projectId?: string): Promise<AuditSummary[]> => {
  if (!projectId) return [];
  const { data } = await apiClient.get<AuditSummary[]>('/audit/offline', {
    params: { project_id: projectId },
  });
  return data;
};

export const getAuditDetail = async (id: string): Promise<AuditResultResponse> => {
  const { data } = await apiClient.get<AuditResultResponse>(`/audit/offline/${id}`);
  return data;
};

