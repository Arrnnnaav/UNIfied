import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

/** Keys verified against serialize_milestone in services/api/app/main.py. */
export interface Milestone {
  id: string;
  goal_id: string;
  title: string;
  description: string;
  badge_title: string;
  target_date: string | null;
  criteria: Record<string, unknown>;
  progress: number;
  status: string;
  completed_at: string | null;
}

/** Keys verified against the GET /api/milestone-shares handler. */
export interface MilestoneShareItem {
  id: string;
  direction: 'received' | 'sent';
  from_student_id: string | null;
  to_student_id: string | null;
  message: string;
  milestone: Milestone | null;
  created_at: string;
}

export const useMilestones = () =>
  useQuery({ queryKey: ['milestones'], queryFn: () => api<Milestone[]>('/api/milestones') });

export const useMilestoneShares = () =>
  useQuery({ queryKey: ['milestone-shares'], queryFn: () => api<MilestoneShareItem[]>('/api/milestone-shares'), retry: false });

export function useMilestoneActions() {
  const client = useQueryClient();
  const invalidate = () => client.invalidateQueries({ queryKey: ['milestones'] });
  const create = useMutation({
    mutationFn: (body: { goal_id?: string; title: string; description: string }) =>
      api<Milestone>('/api/milestones', { method: 'POST', json: body }),
    onSuccess: invalidate,
  });
  const share = useMutation({
    mutationFn: ({ id, ...body }: { id: string; recipient_student_id: string; message: string }) =>
      api<{ id: string; status: string }>(`/api/milestones/${id}/share`, { method: 'POST', json: body }),
  });
  return { create, share };
}
