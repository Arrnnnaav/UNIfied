import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Topic } from '@/api/types';

export interface Assessment { id: string; questions: { prompt: string; options?: string[] }[] }
export interface AttemptResult { score: number; feedback: string; mastery: number }

export function useTopicActions(goalId: string) {
  const client = useQueryClient();
  const invalidate = () => {
    client.invalidateQueries({ queryKey: ['dashboard'] });
    client.invalidateQueries({ queryKey: ['goals', goalId, 'coverage'] });
  };
  const setProgress = useMutation({
    mutationFn: ({ id, progress }: { id: string; progress: 0 | 1 }) => api<Topic>(`/api/topics/${id}/progress`, { method: 'PATCH', json: { progress } }),
    onSuccess: invalidate,
  });
  const addTopic = useMutation({
    mutationFn: (body: { phase_id: string; title: string; description?: string; estimated_minutes?: number }) => api<Topic>('/api/topics', { method: 'POST', json: body }),
    onSuccess: invalidate,
  });
  const startAssessment = useMutation({
    mutationFn: (topicId: string) => api<Assessment>(`/api/topics/${topicId}/assessment`, { method: 'POST', json: {} }),
  });
  const submitAttempt = useMutation({
    mutationFn: ({ id, answers }: { id: string; answers: string[] }) => api<AttemptResult>(`/api/assessments/${id}/attempt`, { method: 'POST', json: { answers } }),
    onSuccess: invalidate,
  });
  return { setProgress, addTopic, startAssessment, submitAttempt };
}
