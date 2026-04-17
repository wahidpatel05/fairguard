import React from 'react';
import type { ContractEvaluationResult } from '../../types';

interface ContractStatusTableProps {
  contracts: ContractEvaluationResult[];
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
            {['Contract ID', 'Attribute', 'Metric', 'Status', 'Value', 'Threshold', 'Explanation'].map((h) => (
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
              <td className="px-4 py-3 text-sm text-gray-600">{c.attribute ?? '—'}</td>
              <td className="px-4 py-3 text-sm text-gray-700">{c.metric}</td>
              <td className="px-4 py-3">
                <span
                  className={`inline-flex items-center font-semibold rounded-full text-xs px-2 py-0.5 border ${
                    c.passed
                      ? 'bg-green-100 text-green-800 border-green-200'
                      : c.severity === 'warn'
                      ? 'bg-amber-100 text-amber-800 border-amber-200'
                      : 'bg-red-100 text-red-800 border-red-200'
                  }`}
                >
                  {c.passed ? 'PASS' : c.severity === 'warn' ? 'WARN' : 'FAIL'}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                {c.value != null ? c.value.toFixed(4) : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                {c.threshold.toFixed(4)}
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

