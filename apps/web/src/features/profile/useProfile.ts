import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Profile } from '@/api/types';

/** GET /api/me/profile adds identity fields on top of serialize_profile (verified in main.py). */
export type ProfileResponse = Profile & {
  student_id: string | null;
  name: string;
  email: string;
  coding_profiles?: Record<string, string>;
};

export interface ProfileUpdate {
  education_stage: string;
  graduation_year: number | null;
  current_skill_level: string;
  known_skills: string[];
  learning_modes: string[];
  preferred_pace: string;
  constraints: string;
  college_name: string;
  college_year: string;
  branch: string;
  college_id: string;
  coding_profiles: Record<string, string>;
}

export const useProfile = () =>
  useQuery({ queryKey: ['profile'], queryFn: () => api<ProfileResponse>('/api/me/profile') });

export function useProfileActions() {
  const client = useQueryClient();
  const update = useMutation({
    mutationFn: (body: ProfileUpdate) => api<ProfileResponse>('/api/me/profile', { method: 'PATCH', json: body }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['profile'] }),
  });
  const deleteAccount = useMutation({
    mutationFn: () => api('/api/me', { method: 'DELETE' }),
  });
  return { update, deleteAccount };
}
