import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Dashboard, ReviewItem, Session } from '@/api/types';

export const useDashboard = () => useQuery({ queryKey: ['dashboard'], queryFn: () => api<Dashboard>('/api/dashboard') });
export const useReviewQueue = () => useQuery({ queryKey: ['review'], queryFn: () => api<ReviewItem[]>('/api/review') });
export function useSessionActions() {
  const client = useQueryClient();
  const invalidate = () => client.invalidateQueries({ queryKey: ['dashboard'] });
  const start = useMutation({ mutationFn: (body: { goal_id: string; topic_id: string | null; kind: string; planned_minutes: number }) => api<Session>('/api/learning-sessions', { method: 'POST', json: body }), onSuccess: invalidate });
  const update = useMutation({ mutationFn: ({ id, ...body }: { id: string; status: string; actual_minutes?: number; notes?: string }) => api<Session>(`/api/learning-sessions/${id}`, { method: 'PATCH', json: body }), onSuccess: invalidate });
  const completeReview = useMutation({ mutationFn: (id: string) => api(`/api/review/${id}/complete`, { method: 'POST' }), onSuccess: () => { invalidate(); client.invalidateQueries({ queryKey: ['review'] }); } });
  return { start, update, completeReview };
}
