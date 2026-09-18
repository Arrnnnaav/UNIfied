import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { SpatialContext } from '@/api/types';

export const useSpatial = () => useQuery({ queryKey: ['spatial'], queryFn: () => api<SpatialContext[]>('/api/spatial-context') });

export function useQuizLater() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<{ due_at?: string }>(`/api/spatial-context/${id}/quiz`, { method: 'POST', json: {} }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['spatial'] });
      client.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}
