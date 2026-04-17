import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import AppLayout from '../components/Layout/AppLayout';
import VerdictBadge from '../components/Common/VerdictBadge';
import { getReceipt, verifyReceipt } from '../api/receipts';

const ReceiptDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: receipt, isLoading, isError } = useQuery({
    queryKey: ['receipt', id],
    queryFn: () => getReceipt(id!),
    enabled: !!id,
  });

  const verifyMutation = useMutation({
    mutationFn: () => verifyReceipt(id!),
    onSuccess: (res) => {
      if (res.valid) {
        toast.success('Receipt verified ✓');
      } else {
        toast.error(`Verification failed: ${res.message}`);
      }
    },
    onError: () => toast.error('Verification request failed'),
  });

  return (
    <AppLayout title="Receipt Detail">
      <div className="max-w-3xl mx-auto space-y-6">
        <button
          onClick={() => navigate('/receipts')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Receipts
        </button>

        {isLoading && (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {isError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-600">
            Failed to load receipt.
          </div>
        )}

        {receipt && (
          <>
            {/* Header */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-1">Fairness Receipt</h2>
                  <p className="text-xs text-gray-400 font-mono">{receipt.id}</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Project: <span className="font-medium text-gray-700">{receipt.project_id}</span>
                  </p>
                  <p className="text-sm text-gray-500">
                    Issued: {new Date(receipt.created_at).toLocaleString()}
                  </p>
                </div>
                <VerdictBadge verdict={receipt.verdict} size="lg" />
              </div>
            </div>

            {/* Verification Result */}
            {verifyMutation.data && (
              <div
                className={`flex items-center gap-3 px-5 py-4 rounded-xl border ${
                  verifyMutation.data.valid
                    ? 'bg-green-50 border-green-200 text-green-700'
                    : 'bg-red-50 border-red-200 text-red-700'
                }`}
              >
                {verifyMutation.data.valid ? (
                  <CheckCircle className="w-5 h-5 flex-shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 flex-shrink-0" />
                )}
                <div>
                  <p className="font-semibold">
                    {verifyMutation.data.valid ? 'Receipt is Valid' : 'Receipt Verification Failed'}
                  </p>
                  <p className="text-sm">{verifyMutation.data.message}</p>
                </div>
              </div>
            )}

            {/* Payload */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Payload</h3>
              <pre className="bg-gray-900 text-green-400 text-xs rounded-lg p-5 overflow-auto max-h-96 font-mono">
                {JSON.stringify(receipt.payload, null, 2)}
              </pre>
            </div>

            {/* Signature */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">
                Signature <span className="text-gray-400 font-normal">(Base64)</span>
              </h3>
              <pre className="bg-gray-50 text-gray-700 text-xs rounded-lg p-4 overflow-auto border border-gray-200 font-mono break-all whitespace-pre-wrap">
                {receipt.signature}
              </pre>
            </div>

            {/* Actions */}
            <div>
              <button
                onClick={() => verifyMutation.mutate()}
                disabled={verifyMutation.isPending}
                className="flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60 transition-colors"
              >
                {verifyMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                Verify Receipt
              </button>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
};

export default ReceiptDetailPage;
