import React from 'react';
import type { RuntimeStatusLevel } from '../../types';

interface TrafficLightProps {
  status: RuntimeStatusLevel | string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const statusConfig: Record<string, { color: string; label: string }> = {
  healthy: { color: 'bg-green-500', label: 'Healthy' },
  warning: { color: 'bg-amber-500', label: 'Warning' },
  critical: { color: 'bg-red-500', label: 'Critical' },
};

const dotSize = { sm: 'w-2.5 h-2.5', md: 'w-3.5 h-3.5', lg: 'w-5 h-5' };

const TrafficLight: React.FC<TrafficLightProps> = ({ status, size = 'md', showLabel = true }) => {
  const config = statusConfig[status] ?? { color: 'bg-gray-400', label: status };
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`${dotSize[size]} ${config.color} rounded-full inline-block animate-pulse`} />
      {showLabel && (
        <span className="text-sm font-medium capitalize text-gray-700">{config.label}</span>
      )}
    </span>
  );
};

export default TrafficLight;
