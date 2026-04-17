import React, { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { UploadCloud, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import AppLayout from '../components/Layout/AppLayout';
import VerdictBadge from '../components/Common/VerdictBadge';
import ContractStatusTable from '../components/Common/ContractStatusTable';
import MetricsBarChart from '../components/Charts/MetricsBarChart';
import { runAudit } from '../api/audits';
import { getProjects } from '../api/projects';
import type { AuditResultResponse } from '../types';
import { extractGroupMetrics } from '../types';

const schema = z.object({
  project_id: z.string().min(1, 'Select a project'),
  target_column: z.string().min(1, 'Target column is required'),
  prediction_column: z.string().min(1, 'Prediction column is required'),
  sensitive_columns: z.string().min(1, 'At least one sensitive column is required'),
  endpoint_id: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

const AuditPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const defaultProjectId = searchParams.get('project') ?? '';
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [result, setResult] = useState<AuditResultResponse | null>(null);
  const [running, setRunning] = useState(false);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { project_id: defaultProjectId },
  });

  const onSubmit = async (data: FormData) => {
    if (!csvFile) {
      toast.error('Please upload a CSV file');
      return;
    }
    setRunning(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', csvFile);
      formData.append('project_id', data.project_id);
      formData.append('target_column', data.target_column);
      formData.append('prediction_column', data.prediction_column);
      formData.append('sensitive_columns', data.sensitive_columns);
      if (data.endpoint_id) formData.append('endpoint_id', data.endpoint_id);

      const res = await runAudit(formData);
      setResult(res);
      toast.success('Audit completed!');
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Audit failed. Please check your inputs.';
      toast.error(message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <AppLayout title="Run Audit">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Form */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-5">New Offline Audit</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Project */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Project</label>
              <Controller
                name="project_id"
                control={control}
                render={({ field }) => (
                  <select
                    {...field}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select a project…</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                )}
              />
              {errors.project_id && (
                <p className="text-red-500 text-xs mt-1">{errors.project_id.message}</p>
              )}
            </div>

            {/* CSV Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Dataset (CSV)</label>
              <label
                className={`flex flex-col items-center justify-center w-full border-2 border-dashed rounded-lg py-8 cursor-pointer transition-colors ${
                  csvFile
                    ? 'border-green-400 bg-green-50'
                    : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
                }`}
              >
                <UploadCloud
                  className={`w-8 h-8 mb-2 ${csvFile ? 'text-green-500' : 'text-gray-400'}`}
                />
                <span className="text-sm text-gray-600">
                  {csvFile ? csvFile.name : 'Click or drag to upload CSV'}
                </span>
                <span className="text-xs text-gray-400 mt-1">CSV files only</span>
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
                />
              </label>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Target column */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target Column
                </label>
                <input
                  {...register('target_column')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. loan_approved"
                />
                {errors.target_column && (
                  <p className="text-red-500 text-xs mt-1">{errors.target_column.message}</p>
                )}
              </div>

              {/* Prediction column */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Prediction Column
                </label>
                <input
                  {...register('prediction_column')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. predicted"
                />
                {errors.prediction_column && (
                  <p className="text-red-500 text-xs mt-1">{errors.prediction_column.message}</p>
                )}
              </div>
            </div>

            {/* Sensitive columns */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sensitive Columns{' '}
                <span className="text-gray-400 font-normal">(comma-separated)</span>
              </label>
              <input
                {...register('sensitive_columns')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. gender, race, age_group"
              />
              {errors.sensitive_columns && (
                <p className="text-red-500 text-xs mt-1">{errors.sensitive_columns.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={running}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {running ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Running Audit…
                </>
              ) : (
                'Run Audit'
              )}
            </button>
          </form>
        </div>

        {/* Result */}
        {result && <AuditResultView result={result} />}
      </div>
    </AppLayout>
  );
};

export const AuditResultView: React.FC<{ result: AuditResultResponse }> = ({ result }) => {
  const groupMetrics = extractGroupMetrics(result.audit.metrics_json);

  return (
    <div className="space-y-6">
      {/* Overall Verdict */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-4">
          <div>
            <p className="text-sm text-gray-500 mb-1">Overall Verdict</p>
            <VerdictBadge verdict={result.audit.verdict ?? 'UNKNOWN'} size="lg" />
          </div>
          {result.receipt_id && (
            <div className="ml-auto">
              <Link
                to={`/receipts/${result.receipt_id}`}
                className="text-sm text-blue-600 hover:underline"
              >
                View Fairness Receipt →
              </Link>
            </div>
          )}
        </div>

        {/* Global metrics summary */}
        {result.audit.metrics_json?.global && (
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Total Rows</p>
              <p className="text-xl font-bold text-gray-900">
                {result.audit.metrics_json.global.total_rows}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Positive Outcome Rate</p>
              <p className="text-xl font-bold text-gray-900">
                {(result.audit.metrics_json.global.positive_outcome_rate * 100).toFixed(1)}%
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Overall Accuracy</p>
              <p className="text-xl font-bold text-gray-900">
                {(result.audit.metrics_json.global.overall_accuracy * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Contract Evaluations */}
      {result.contract_evaluations.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-base font-semibold text-gray-900 mb-4">Contract Evaluations</h3>
          <ContractStatusTable contracts={result.contract_evaluations} />
        </div>
      )}

      {/* Recommendations */}
      {result.recommendations.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-base font-semibold text-gray-900 mb-4">Recommendations</h3>
          <ul className="space-y-3">
            {result.recommendations.map((rec, i) => (
              <li key={i} className="flex gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <span className="text-amber-500 mt-0.5 flex-shrink-0">⚠</span>
                <div>
                  {rec.title && <p className="text-sm font-semibold text-gray-900">{String(rec.title)}</p>}
                  {rec.description && <p className="text-sm text-gray-600 mt-0.5">{String(rec.description)}</p>}
                  {rec.metric && (
                    <p className="text-xs text-gray-400 mt-1">
                      Metric: {String(rec.metric)}
                      {rec.attribute ? ` · Attribute: ${String(rec.attribute)}` : ''}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Group Metrics */}
      {groupMetrics.length > 0 && (
        <>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Per-Group Metrics</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {['Group', 'Approval Rate', 'TPR', 'FPR', 'Accuracy'].map((h) => (
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
                  {groupMetrics.map((g, i) => (
                    <tr key={`${g.group}-${i}`} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{g.group}</td>
                      <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                        {g.approval_rate.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                        {g.tpr.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                        {g.fpr.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                        {g.accuracy.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Metrics by Group</h3>
            <MetricsBarChart data={groupMetrics} />
          </div>
        </>
      )}
    </div>
  );
};

export default AuditPage;
