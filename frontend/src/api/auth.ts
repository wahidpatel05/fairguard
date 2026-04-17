import apiClient from './client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const login = async (email: string, password: string): Promise<TokenResponse> => {
  const params = new URLSearchParams();
  params.append('username', email);
  params.append('password', password);
  const { data } = await apiClient.post<TokenResponse>('/auth/token', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
};

export const register = async (payload: RegisterRequest): Promise<User> => {
  const { data } = await apiClient.post<User>('/auth/register', payload);
  return data;
};

export const getMe = async (): Promise<User> => {
  const { data } = await apiClient.get<User>('/auth/me');
  return data;
};
