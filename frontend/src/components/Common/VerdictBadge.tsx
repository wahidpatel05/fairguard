import React from 'react';
import type { Verdict } from '../../types';

interface VerdictBadgeProps {
  verdict: Verdict | string;
  size?: 'sm' | 'md' | 'lg';
}

const verdictConfig: Record<string, { label: string; className: string }> = {
  PASS: { label: 'PASS', className: 'bg-green-100 text-green-800 border border-green-200' },
  FAIL: { label: 'FAIL', className: 'bg-red-100 text-red-800 border border-red-200' },
  PASS_WITH_WARNINGS: { label: 'PASS WITH WARNINGS', className: 'bg-amber-100 text-amber-800 border border-amber-200' },
};

const sizeClass = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
  lg: 'text-base px-3 py-1.5',
};

const VerdictBadge: React.FC<VerdictBadgeProps> = ({ verdict, size = 'md' }) => {
  const config = verdictConfig[verdict] ?? { label: verdict, className: 'bg-gray-100 text-gray-800 border border-gray-200' };
  return (
    <span className={`inline-flex items-center font-semibold rounded-full ${config.className} ${sizeClass[size]}`}>
      {config.label}
    </span>
  );
};

export default VerdictBadge;
