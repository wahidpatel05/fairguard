import apiClient from './client';

export interface Receipt {
  id: string;
  project_id: string;
  audit_id?: string;
  verdict: 'PASS' | 'FAIL' | 'PASS_WITH_WARNINGS';
  payload: Record<string, unknown>;
  signature: string;
  created_at: string;
}

export interface ReceiptFilters {
  project_id?: string;
  date_from?: string;
  date_to?: string;
}

export interface VerifyResult {
  valid: boolean;
  message: string;
}

export const getReceipts = async (filters?: ReceiptFilters): Promise<Receipt[]> => {
  const { data } = await apiClient.get<Receipt[]>('/receipts/', { params: filters });
  return data;
};

export const getReceipt = async (id: string): Promise<Receipt> => {
  const { data } = await apiClient.get<Receipt>(`/receipts/${id}`);
  return data;
};

export const verifyReceipt = async (id: string): Promise<VerifyResult> => {
  const { data } = await apiClient.post<VerifyResult>(`/receipts/${id}/verify`);
  return data;
};
