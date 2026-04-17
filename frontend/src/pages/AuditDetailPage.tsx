import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, FileCheck2 } from 'lucide-react';
import AppLayout from '../components/Layout/AppLayout';
import { AuditResultView } from './AuditPage';
import { getAuditDetail } from '../api/audits';

const AuditDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: audit, isLoading, isError } = useQuery({
    queryKey: ['auditDetail', id],
    queryFn: () => getAuditDetail(id!),
    enabled: !!id,
  });

  return (
    <AppLayout title="Audit Detail">
      <div className="max-w-4xl mx-auto space-y-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        {isLoading && (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {isError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center text-red-600">
            Failed to load audit. It may not exist or you may not have permission.
          </div>
        )}

        {audit && (
          <>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <p className="text-xs text-gray-400 font-mono mb-1">Audit ID: {audit.id}</p>
                  <p className="text-sm text-gray-500">
                    Project: {audit.project_id}
                    {audit.endpoint_id && ` · Endpoint: ${audit.endpoint_id}`}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(audit.created_at).toLocaleString()}
                  </p>
                </div>
                {audit.result?.receipt_id && (
                  <Link
                    to={`/receipts/${audit.result.receipt_id}`}
                    className="flex items-center gap-2 bg-green-50 text-green-700 border border-green-200 px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-100 transition-colors"
                  >
                    <FileCheck2 className="w-4 h-4" /> View Fairness Receipt
                  </Link>
                )}
              </div>
            </div>

            {audit.result ? (
              <AuditResultView result={audit.result} />
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
                Detailed results not available for this audit.
              </div>
            )}
          </>
        )}
      </div>
    </AppLayout>
  );
};

export default AuditDetailPage;
