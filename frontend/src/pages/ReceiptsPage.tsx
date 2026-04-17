import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle, XCircle, Eye, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import AppLayout from '../components/Layout/AppLayout';
import VerdictBadge from '../components/Common/VerdictBadge';
import { getProjects } from '../api/projects';
import { getReceipts, verifyReceipt, type Receipt } from '../api/receipts';

const ReceiptDetailModal: React.FC<{
  receipt: Receipt;
  onClose: () => void;
}> = ({ receipt, onClose }) => {
  const verifyMutation = useMutation({
    mutationFn: () => verifyReceipt(receipt.id),
    onSuccess: (res) => {
      if (res.valid) {
        toast.success('Receipt is valid ✓');
      } else {
        toast.error(`Verification failed: ${res.message}`);
      }
    },
    onError: () => toast.error('Verification request failed'),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Fairness Receipt</h2>
            <p className="text-xs text-gray-400 font-mono mt-0.5">{receipt.id}</p>
          </div>
          <div className="flex items-center gap-3">
            <VerdictBadge verdict={receipt.verdict} size="sm" />
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            >
              ×
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Timestamp
            </p>
            <p className="text-sm text-gray-700">{new Date(receipt.created_at).toLocaleString()}</p>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Payload
            </p>
            <pre className="bg-gray-900 text-green-400 text-xs rounded-lg p-4 overflow-auto max-h-48 font-mono">
              {JSON.stringify(receipt.payload, null, 2)}
            </pre>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Signature (Base64)
            </p>
            <pre className="bg-gray-50 text-gray-700 text-xs rounded-lg p-3 overflow-auto max-h-24 font-mono border border-gray-200 break-all whitespace-pre-wrap">
              {receipt.signature}
            </pre>
          </div>

          {verifyMutation.data && (
            <div
              className={`flex items-center gap-2 px-4 py-3 rounded-lg border ${
                verifyMutation.data.valid
                  ? 'bg-green-50 border-green-200 text-green-700'
                  : 'bg-red-50 border-red-200 text-red-700'
              }`}
            >
              {verifyMutation.data.valid ? (
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 flex-shrink-0" />
              )}
              <span className="text-sm font-medium">{verifyMutation.data.message}</span>
            </div>
          )}
        </div>

        <div className="p-5 border-t border-gray-200 flex gap-3">
          <button
            onClick={() => verifyMutation.mutate()}
            disabled={verifyMutation.isPending}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            {verifyMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
            Verify Receipt
          </button>
          <Link
            to={`/receipts/${receipt.id}`}
            className="flex items-center gap-2 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            <Eye className="w-4 h-4" /> Full Detail
          </Link>
          <button
            onClick={onClose}
            className="ml-auto px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

const ReceiptsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [selectedProject, setSelectedProject] = useState(searchParams.get('project') ?? '');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [viewReceipt, setViewReceipt] = useState<Receipt | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });

  const { data: receipts = [], isLoading } = useQuery({
    queryKey: ['receipts', selectedProject, dateFrom, dateTo],
    queryFn: () =>
      getReceipts({
        project_id: selectedProject || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  });

  const verifyMutation = useMutation({
    mutationFn: verifyReceipt,
    onSuccess: (res) => {
      if (res.valid) {
        toast.success('Receipt verified ✓');
      } else {
        toast.error(`Verification failed: ${res.message}`);
      }
    },
    onError: () => toast.error('Verification failed'),
  });

  return (
    <AppLayout title="Fairness Receipts">
      <div className="space-y-6">
        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Project</label>
              <select
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-40"
              >
                <option value="">All projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : receipts.length === 0 ? (
          <div className="bg-white rounded-xl border border-dashed border-gray-300 p-16 text-center text-gray-400">
            No fairness receipts found.
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['Receipt ID', 'Project', 'Verdict', 'Timestamp', 'Actions'].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {receipts.map((receipt) => {
                  const project = projects.find((p) => p.id === receipt.project_id);
                  return (
                    <tr key={receipt.id} className="hover:bg-gray-50">
                      <td className="px-5 py-3 text-sm font-mono text-gray-600">
                        {receipt.id.slice(0, 12)}…
                      </td>
                      <td className="px-5 py-3 text-sm text-gray-700">
                        {project?.name ?? receipt.project_id}
                      </td>
                      <td className="px-5 py-3">
                        <VerdictBadge verdict={receipt.verdict} size="sm" />
                      </td>
                      <td className="px-5 py-3 text-sm text-gray-500">
                        {new Date(receipt.created_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => setViewReceipt(receipt)}
                            className="text-sm text-blue-600 hover:underline"
                          >
                            View
                          </button>
                          <button
                            onClick={() => verifyMutation.mutate(receipt.id)}
                            disabled={verifyMutation.isPending}
                            className="text-sm text-gray-500 hover:text-gray-900"
                          >
                            Verify
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {viewReceipt && (
        <ReceiptDetailModal receipt={viewReceipt} onClose={() => setViewReceipt(null)} />
      )}
    </AppLayout>
  );
};

export default ReceiptsPage;
