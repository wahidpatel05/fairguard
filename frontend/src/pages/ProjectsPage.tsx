import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Pencil, Trash2, X } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import AppLayout from '../components/Layout/AppLayout';
import { getProjects, createProject, updateProject, deleteProject, type Project } from '../api/projects';

const schema = z.object({
  name: z.string().min(2, 'Name is required'),
  domain: z.string().min(1, 'Domain is required'),
  description: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

const DOMAINS = ['lending', 'hiring', 'healthcare', 'insurance', 'education', 'other'];

const ProjectModal: React.FC<{
  onClose: () => void;
  initial?: Project;
}> = ({ onClose, initial }) => {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: initial ? { name: initial.name, domain: initial.domain, description: initial.description } : {},
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      initial ? updateProject(initial.id, data) : createProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success(initial ? 'Project updated' : 'Project created');
      onClose();
    },
    onError: () => toast.error('Failed to save project'),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-gray-900">
            {initial ? 'Edit Project' : 'Create Project'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Project Name</label>
            <input
              {...register('name')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="My AI Project"
            />
            {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
            <select
              {...register('domain')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select domain…</option>
              {DOMAINS.map((d) => (
                <option key={d} value={d}>
                  {d.charAt(0).toUpperCase() + d.slice(1)}
                </option>
              ))}
            </select>
            {errors.domain && <p className="text-red-500 text-xs mt-1">{errors.domain.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-gray-400">(optional)</span>
            </label>
            <textarea
              {...register('description')}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Brief description of the project"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60 transition-colors"
            >
              {isSubmitting ? 'Saving…' : initial ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const ProjectsPage: React.FC = () => {
  const [showModal, setShowModal] = useState(false);
  const [editProject, setEditProject] = useState<Project | null>(null);
  const queryClient = useQueryClient();

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project deleted');
    },
    onError: () => toast.error('Failed to delete project'),
  });

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Delete project "${name}"? This cannot be undone.`)) {
      deleteMutation.mutate(id);
    }
  };

  const domainColors: Record<string, string> = {
    lending: 'bg-blue-100 text-blue-700',
    hiring: 'bg-purple-100 text-purple-700',
    healthcare: 'bg-green-100 text-green-700',
    insurance: 'bg-amber-100 text-amber-700',
    education: 'bg-pink-100 text-pink-700',
    other: 'bg-gray-100 text-gray-600',
  };

  return (
    <AppLayout title="Projects">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <p className="text-gray-500 text-sm">{projects.length} project{projects.length !== 1 ? 's' : ''}</p>
          <button
            onClick={() => { setEditProject(null); setShowModal(true); }}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" /> New Project
          </button>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
                <div className="h-3 bg-gray-100 rounded w-1/5" />
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="bg-white rounded-xl border border-dashed border-gray-300 p-16 text-center">
            <p className="text-gray-400 text-lg mb-4">No projects yet</p>
            <button
              onClick={() => { setEditProject(null); setShowModal(true); }}
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4" /> Create your first project
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['Name', 'Domain', 'Description', 'Created', 'Actions'].map((h) => (
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
                {projects.map((project) => (
                  <tr key={project.id} className="hover:bg-gray-50">
                    <td className="px-5 py-4">
                      <Link
                        to={`/projects/${project.id}`}
                        className="font-medium text-blue-600 hover:underline"
                      >
                        {project.name}
                      </Link>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                          domainColors[project.domain?.toLowerCase()] ?? 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {project.domain}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-500 max-w-xs truncate">
                      {project.description || '—'}
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-500">
                      {new Date(project.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => { setEditProject(project); setShowModal(true); }}
                          className="text-gray-400 hover:text-blue-600 transition-colors"
                          title="Edit"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(project.id, project.name)}
                          className="text-gray-400 hover:text-red-600 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <ProjectModal
          onClose={() => { setShowModal(false); setEditProject(null); }}
          initial={editProject ?? undefined}
        />
      )}
    </AppLayout>
  );
};

export default ProjectsPage;
