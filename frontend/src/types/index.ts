export type Verdict = 'PASS' | 'FAIL' | 'PASS_WITH_WARNINGS';
export type RuntimeStatusLevel = 'healthy' | 'warning' | 'critical';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}
