import React, { useState } from 'react';
import { Info } from 'lucide-react';

interface MetricCardProps {
  name: string;
  value: number | string;
  explanation?: string;
  status?: 'pass' | 'fail' | 'warning' | 'neutral';
}

const statusColors: Record<string, string> = {
  pass: 'border-green-300 bg-green-50',
  fail: 'border-red-300 bg-red-50',
  warning: 'border-amber-300 bg-amber-50',
  neutral: 'border-gray-200 bg-white',
};

const MetricCard: React.FC<MetricCardProps> = ({ name, value, explanation, status = 'neutral' }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className={`border rounded-lg p-4 relative ${statusColors[status]}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{name}</span>
        {explanation && (
          <div className="relative">
            <button
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              className="text-gray-400 hover:text-gray-600"
              type="button"
            >
              <Info className="w-4 h-4" />
            </button>
            {showTooltip && (
              <div className="absolute right-0 top-6 z-50 w-56 bg-gray-900 text-white text-xs rounded-lg p-2.5 shadow-lg">
                {explanation}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="text-2xl font-bold text-gray-900">
        {typeof value === 'number' ? value.toFixed(4) : value}
      </div>
    </div>
  );
};

export default MetricCard;
