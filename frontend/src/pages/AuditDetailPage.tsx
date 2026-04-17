import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, FileCheck2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/Layout/AppLayout';
import { AuditResultView } from './AuditPage';
import { getAuditDetail } from '../api/audits';

const AuditDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: auditResult, isLoading, isError } = useQuery({
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

        {auditResult && (
          <>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <p className="text-xs text-gray-400 font-mono mb-1">
                    Audit ID: {auditResult.audit.id}
                  </p>
                  <p className="text-sm text-gray-500">
                    Project: {auditResult.audit.project_id}
                    {auditResult.audit.target_column &&
                      ` · Target: ${auditResult.audit.target_column}`}
                    {auditResult.audit.prediction_column &&
                      ` · Prediction: ${auditResult.audit.prediction_column}`}
                  </p>
                  {auditResult.audit.sensitive_columns &&
                    auditResult.audit.sensitive_columns.length > 0 && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        Sensitive: {auditResult.audit.sensitive_columns.join(', ')}
                      </p>
                    )}
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(auditResult.audit.created_at).toLocaleString()}
                  </p>
                </div>
                {auditResult.receipt_id && (
                  <Link
                    to={`/receipts/${auditResult.receipt_id}`}
                    className="flex items-center gap-2 bg-green-50 text-green-700 border border-green-200 px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-100 transition-colors"
                  >
                    <FileCheck2 className="w-4 h-4" /> View Fairness Receipt
                  </Link>
                )}
              </div>
            </div>

            <AuditResultView result={auditResult} />
          </>
        )}
      </div>
    </AppLayout>
  );
};

export default AuditDetailPage;

