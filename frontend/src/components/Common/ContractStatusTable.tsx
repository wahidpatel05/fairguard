import React from 'react';
import type { ContractResult } from '../../api/audits';
import VerdictBadge from './VerdictBadge';

interface ContractStatusTableProps {
  contracts: ContractResult[];
}

const ContractStatusTable: React.FC<ContractStatusTableProps> = ({ contracts }) => {
  if (!contracts || contracts.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">No contract evaluations available.</div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {['Contract ID', 'Metric', 'Status', 'Value', 'Threshold', 'Explanation'].map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {contracts.map((c, i) => (
            <tr key={`${c.contract_id}-${i}`} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{c.contract_id}</td>
              <td className="px-4 py-3 text-sm text-gray-700">{c.metric}</td>
              <td className="px-4 py-3">
                <VerdictBadge verdict={c.status} size="sm" />
              </td>
              <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                {typeof c.value === 'number' ? c.value.toFixed(4) : c.value}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                {typeof c.threshold === 'number' ? c.threshold.toFixed(4) : c.threshold}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500 max-w-xs">{c.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ContractStatusTable;
