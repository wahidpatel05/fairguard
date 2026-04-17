import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, ClipboardCheck, Activity, Trash2, CheckCircle, Loader2, X } from 'lucide-react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import AppLayout from '../components/Layout/AppLayout';
import VerdictBadge from '../components/Common/VerdictBadge';
import { getProject } from '../api/projects';
import { getAuditLogs } from '../api/audits';
import {
  getContracts,
  createContract,
  activateContract,
  deleteContract,
  type ContractOut,
} from '../api/contracts';
import type { ContractRule } from '../types';

type Tab = 'audits' | 'contracts' | 'runtime' | 'receipts';

// ── Contract creation form ──────────────────────────────────────────────────

const ruleSchema = z.object({
  id: z.string().min(1, 'Rule ID required'),
  metric: z.string().min(1, 'Metric required'),
  threshold: z.number(),
  operator: z.enum(['gte', 'lte']),
  sensitive_column: z.string().optional(),
  description: z.string().optional(),
});

const contractSchema = z.object({
  notes: z.string().optional(),
  contracts: z.array(ruleSchema).min(1, 'Add at least one rule'),
});

type ContractFormData = z.infer<typeof contractSchema>;

const METRICS = [
  'disparate_impact',
  'tpr_difference',
  'fpr_difference',
  'accuracy_difference',
];

const CreateContractModal: React.FC<{
  projectId: string;
  onClose: () => void;
}> = ({ projectId, onClose }) => {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ContractFormData>({
    resolver: zodResolver(contractSchema),
    defaultValues: {
      notes: '',
      contracts: [
        { id: 'rule-1', metric: 'disparate_impact', threshold: 0.8, operator: 'gte' },
      ],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'contracts' });

  const mutation = useMutation({
    mutationFn: (data: ContractFormData) =>
      createContract(projectId, {
        contracts: data.contracts as ContractRule[],
        notes: data.notes || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts', projectId] });
      toast.success('Contract version created');
      onClose();
    },
    onError: () => toast.error('Failed to create contract'),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">New Contract Version</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form
          onSubmit={handleSubmit((d) => mutation.mutate(d))}
          className="flex-1 overflow-y-auto p-5 space-y-5"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              {...register('notes')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Initial contract v1"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">Rules</h3>
              <button
                type="button"
                onClick={() =>
                  append({
                    id: `rule-${fields.length + 1}`,
                    metric: 'disparate_impact',
                    threshold: 0.8,
                    operator: 'gte',
                  })
                }
                className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                <Plus className="w-3.5 h-3.5" /> Add Rule
              </button>
            </div>
            {typeof errors.contracts?.message === 'string' && (
              <p className="text-red-500 text-xs mb-2">{errors.contracts.message}</p>
            )}

            <div className="space-y-3">
              {fields.map((field, idx) => (
                <div
                  key={field.id}
                  className="bg-gray-50 rounded-lg p-4 border border-gray-200"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-semibold text-gray-500 uppercase">
                      Rule {idx + 1}
                    </span>
                    {fields.length > 1 && (
                      <button
                        type="button"
                        onClick={() => remove(idx)}
                        className="text-gray-400 hover:text-red-500"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Rule ID</label>
                      <input
                        {...register(`contracts.${idx}.id`)}
                        className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                        placeholder="rule-1"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Metric</label>
                      <select
                        {...register(`contracts.${idx}.metric`)}
                        className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                      >
                        {METRICS.map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Operator
                      </label>
                      <select
                        {...register(`contracts.${idx}.operator`)}
                        className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                      >
                        <option value="gte">≥ (gte)</option>
                        <option value="lte">≤ (lte)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Threshold
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        {...register(`contracts.${idx}.threshold`)}
                        className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Sensitive Column{' '}
                        <span className="text-gray-400 font-normal">(optional)</span>
                      </label>
                      <input
                        {...register(`contracts.${idx}.sensitive_column`)}
                        className="w-full px-2.5 py-1.5 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                        placeholder="e.g. gender"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || mutation.isPending}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
            >
              {mutation.isPending ? (
                <span className="flex items-center justify-center gap-1.5">
                  <Loader2 className="w-4 h-4 animate-spin" /> Saving…
                </span>
              ) : (
                'Create Contract'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const ContractsTab: React.FC<{ projectId: string }> = ({ projectId }) => {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data: contracts = [], isLoading } = useQuery({
    queryKey: ['contracts', projectId],
    queryFn: () => getContracts(projectId),
  });

  const activateMutation = useMutation({
    mutationFn: (contractId: string) => activateContract(projectId, contractId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts', projectId] });
      toast.success('Contract activated');
    },
    onError: () => toast.error('Failed to activate contract'),
  });

  const deleteMutation = useMutation({
    mutationFn: (contractId: string) => deleteContract(projectId, contractId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts', projectId] });
      toast.success('Contract deleted');
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to delete contract';
      toast.error(msg);
    },
  });

  const handleDelete = (c: ContractOut) => {
    if (c.is_current) {
      toast.error('Cannot delete the active contract');
      return;
    }
    if (confirm(`Delete contract v${c.version}? This cannot be undone.`)) {
      deleteMutation.mutate(c.id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {contracts.length} version{contracts.length !== 1 ? 's' : ''}
        </p>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" /> New Version
        </button>
      </div>

      {contracts.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-400 mb-4">No fairness contracts yet.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" /> Create First Contract
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {contracts.map((c) => (
            <div
              key={c.id}
              className={`bg-white rounded-xl border p-5 ${
                c.is_current ? 'border-blue-300 ring-1 ring-blue-300' : 'border-gray-200'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-semibold text-gray-900">
                      Version {c.version}
                    </span>
                    {c.is_current && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                        Active
                      </span>
                    )}
                  </div>
                  {c.notes && <p className="text-sm text-gray-500">{c.notes}</p>}
                  <p className="text-xs text-gray-400 mt-1">
                    Created {new Date(c.created_at).toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-400">
                    {c.contracts_json.rules?.length ?? 0} rule
                    {(c.contracts_json.rules?.length ?? 0) !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {!c.is_current && (
                    <button
                      onClick={() => activateMutation.mutate(c.id)}
                      disabled={activateMutation.isPending}
                      className="flex items-center gap-1.5 text-xs text-green-700 bg-green-50 border border-green-200 px-3 py-1.5 rounded-lg hover:bg-green-100 transition-colors disabled:opacity-60"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Activate
                    </button>
                  )}
                  {!c.is_current && (
                    <button
                      onClick={() => handleDelete(c)}
                      disabled={deleteMutation.isPending}
                      className="text-gray-400 hover:text-red-600 transition-colors disabled:opacity-60"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Rules preview */}
              {c.contracts_json.rules && c.contracts_json.rules.length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-xs divide-y divide-gray-100">
                    <thead>
                      <tr className="text-gray-500">
                        <th className="text-left pb-2 pr-4">ID</th>
                        <th className="text-left pb-2 pr-4">Metric</th>
                        <th className="text-left pb-2 pr-4">Operator</th>
                        <th className="text-left pb-2 pr-4">Threshold</th>
                        <th className="text-left pb-2">Column</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {c.contracts_json.rules.map((rule) => (
                        <tr key={rule.id} className="text-gray-700">
                          <td className="py-1.5 pr-4 font-medium">{rule.id}</td>
                          <td className="py-1.5 pr-4">{rule.metric}</td>
                          <td className="py-1.5 pr-4">{rule.operator}</td>
                          <td className="py-1.5 pr-4 font-mono">{rule.threshold}</td>
                          <td className="py-1.5">{rule.sensitive_column ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateContractModal projectId={projectId} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
};

// ── Main Page ───────────────────────────────────────────────────────────────

const domainColors: Record<string, string> = {
  lending: 'bg-blue-100 text-blue-700',
  hiring: 'bg-purple-100 text-purple-700',
  healthcare: 'bg-green-100 text-green-700',
  insurance: 'bg-amber-100 text-amber-700',
  education: 'bg-pink-100 text-pink-700',
  other: 'bg-gray-100 text-gray-600',
};

const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('audits');

  const { data: project, isLoading: loadingProject } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  });

  const { data: audits = [], isLoading: loadingAudits } = useQuery({
    queryKey: ['auditLogs', id],
    queryFn: () => getAuditLogs(id!),
    enabled: !!id,
  });

  const tabs: { key: Tab; label: string }[] = [
    { key: 'audits', label: 'Audits' },
    { key: 'contracts', label: 'Contracts' },
    { key: 'runtime', label: 'Runtime' },
    { key: 'receipts', label: 'Receipts' },
  ];

  if (loadingProject) {
    return (
      <AppLayout title="Project Detail">
        <div className="flex justify-center py-20">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      </AppLayout>
    );
  }

  if (!project) {
    return (
      <AppLayout title="Project Detail">
        <div className="text-center py-20 text-gray-500">Project not found.</div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title={project.name}>
      <div className="space-y-6">
        {/* Back */}
        <button
          onClick={() => navigate('/projects')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Projects
        </button>

        {/* Header */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-2xl font-bold text-gray-900">{project.name}</h2>
                <span
                  className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                    domainColors[project.domain?.toLowerCase()] ?? 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {project.domain}
                </span>
              </div>
              {project.description && (
                <p className="text-gray-500 text-sm">{project.description}</p>
              )}
              <p className="text-xs text-gray-400 mt-2">
                Created {new Date(project.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => navigate(`/audit/new?project=${project.id}`)}
                className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                <ClipboardCheck className="w-4 h-4" /> New Audit
              </button>
              <button
                onClick={() => navigate(`/runtime?project=${project.id}`)}
                className="flex items-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                <Activity className="w-4 h-4" /> Runtime
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div>
          <div className="flex gap-1 border-b border-gray-200 mb-4">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Audits Tab */}
          {activeTab === 'audits' && (
            <div>
              {loadingAudits ? (
                <div className="flex justify-center py-8">
                  <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : audits.length === 0 ? (
                <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
                  <p className="text-gray-400 mb-4">No audits yet for this project.</p>
                  <button
                    onClick={() => navigate(`/audit/new?project=${project.id}`)}
                    className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" /> Run First Audit
                  </button>
                </div>
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-100">
                    <thead className="bg-gray-50">
                      <tr>
                        {['Audit ID', 'File', 'Verdict', 'Date', ''].map((h) => (
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
                      {audits.map((audit) => (
                        <tr key={audit.id} className="hover:bg-gray-50">
                          <td className="px-5 py-3 text-sm font-mono text-gray-600">
                            {audit.id.slice(0, 8)}…
                          </td>
                          <td className="px-5 py-3 text-sm text-gray-500 max-w-xs truncate">
                            {audit.dataset_filename ?? '—'}
                          </td>
                          <td className="px-5 py-3">
                            <VerdictBadge verdict={audit.verdict ?? 'UNKNOWN'} size="sm" />
                          </td>
                          <td className="px-5 py-3 text-sm text-gray-500">
                            {new Date(audit.created_at).toLocaleString()}
                          </td>
                          <td className="px-5 py-3 text-right">
                            <Link
                              to={`/audit/${audit.id}`}
                              className="text-sm text-blue-600 hover:underline"
                            >
                              View
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Contracts Tab */}
          {activeTab === 'contracts' && <ContractsTab projectId={project.id} />}

          {/* Runtime Tab */}
          {activeTab === 'runtime' && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <p className="text-gray-500 mb-4">View real-time monitoring for this project.</p>
              <button
                onClick={() => navigate(`/runtime?project=${project.id}`)}
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                <Activity className="w-4 h-4" /> Open Runtime Dashboard
              </button>
            </div>
          )}

          {/* Receipts Tab */}
          {activeTab === 'receipts' && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <p className="text-gray-500 mb-4">View fairness receipts for this project.</p>
              <Link
                to={`/receipts?project=${project.id}`}
                className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                View Receipts
              </Link>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default ProjectDetailPage;
