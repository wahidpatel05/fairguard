import apiClient from './client';
import type { Project, CreateProjectRequest } from '../types';

export type { Project, CreateProjectRequest };

export const getProjects = async (): Promise<Project[]> => {
  const { data } = await apiClient.get<Project[]>('/projects/');
  return data;
};

export const getProject = async (id: string): Promise<Project> => {
  const { data } = await apiClient.get<Project>(`/projects/${id}`);
  return data;
};

export const createProject = async (payload: CreateProjectRequest): Promise<Project> => {
  const { data } = await apiClient.post<Project>('/projects/', payload);
  return data;
};

export const updateProject = async (id: string, payload: Partial<CreateProjectRequest>): Promise<Project> => {
  const { data } = await apiClient.put<Project>(`/projects/${id}`, payload);
  return data;
};

export const deleteProject = async (id: string): Promise<void> => {
  await apiClient.delete(`/projects/${id}`);
};

