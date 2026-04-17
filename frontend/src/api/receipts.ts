import apiClient from './client';
import type { FairnessReceipt, VerifyResult } from '../types';

export type { FairnessReceipt, VerifyResult };

export interface ReceiptFilters {
  project_id?: string;
  date_from?: string;
  date_to?: string;
}

export const getReceipts = async (filters?: ReceiptFilters): Promise<FairnessReceipt[]> => {
  const { data } = await apiClient.get<FairnessReceipt[]>('/receipts/', { params: filters });
  return data;
};

export const getReceipt = async (id: string): Promise<FairnessReceipt> => {
  const { data } = await apiClient.get<FairnessReceipt>(`/receipts/${id}`);
  return data;
};

export const verifyReceipt = async (id: string): Promise<VerifyResult> => {
  const { data } = await apiClient.post<VerifyResult>(`/receipts/${id}/verify`);
  return data;
};

