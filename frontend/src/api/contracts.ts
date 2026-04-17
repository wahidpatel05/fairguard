import apiClient from './client';
import type { ContractOut, ContractCreate } from '../types';

export type { ContractOut, ContractCreate };

export const getContracts = async (projectId: string): Promise<ContractOut[]> => {
  const { data } = await apiClient.get<ContractOut[]>(`/projects/${projectId}/contracts/`);
  return data;
};

export const getCurrentContract = async (projectId: string): Promise<ContractOut> => {
  const { data } = await apiClient.get<ContractOut>(`/projects/${projectId}/contracts/current`);
  return data;
};

export const createContract = async (projectId: string, payload: ContractCreate): Promise<ContractOut> => {
  const { data } = await apiClient.post<ContractOut>(`/projects/${projectId}/contracts/`, payload);
  return data;
};

export const activateContract = async (projectId: string, contractId: string): Promise<ContractOut> => {
  const { data } = await apiClient.post<ContractOut>(
    `/projects/${projectId}/contracts/${contractId}/activate`,
  );
  return data;
};

export const deleteContract = async (projectId: string, contractId: string): Promise<void> => {
  await apiClient.delete(`/projects/${projectId}/contracts/${contractId}`);
};
