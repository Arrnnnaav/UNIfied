import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

export interface IngestionJob { id: string; resource_id: string; kind: string; status: string; progress: number; error: string | null }
export interface Resource { id: string; title: string; source_type: string; status: string; trust_status: string }
export interface SearchResult { resource_id: string; title: string; snippet: string; score: number }

export function useIngestionJobs() {
  return useQuery({
    queryKey: ['ingestion-jobs'],
    queryFn: () => api<IngestionJob[]>('/api/ingestion/jobs'),
    refetchInterval: (query) => {
      const jobs = query.state.data;
      return jobs?.some(j => j.status === 'queued' || j.status === 'running') ? 3000 : false;
    },
  });
}

export const useSearch = (q: string, goalId?: string) => useQuery({
  queryKey: ['search', q, goalId],
  queryFn: () => api<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}${goalId ? `&goal_id=${goalId}` : ''}`),
  enabled: q.trim().length > 0,
});

export function useResourceActions(goalId: string) {
  const client = useQueryClient();
  const invalidate = () => {
    client.invalidateQueries({ queryKey: ['dashboard'] });
    client.invalidateQueries({ queryKey: ['ingestion-jobs'] });
  };
  const createResource = useMutation({
    mutationFn: (body: { goal_id: string; title: string; source_type: 'text' | 'url' | 'github' | 'youtube'; content?: string; url?: string }) =>
      api<Resource>('/api/resources', { method: 'POST', json: body }),
    onSuccess: invalidate,
  });
  const ingest = useMutation({
    mutationFn: ({ id, kind, url }: { id: string; kind: 'url' | 'github' | 'youtube'; url: string }) =>
      api(`/api/resources/${id}/ingest-${kind}`, { method: 'POST', json: { url } }),
    onSuccess: invalidate,
  });
  const upload = useMutation({
    mutationFn: ({ file, title }: { file: File; title: string }) => {
      const form = new FormData();
      form.append('file', file);
      form.append('goal_id', goalId);
      form.append('title', title);
      return api<Resource>('/api/resources/upload', { method: 'POST', body: form });
    },
    onSuccess: invalidate,
  });
  return { createResource, ingest, upload };
}
