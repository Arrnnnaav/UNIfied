import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { api, ApiError } from '@/api/client';
import type { Goal, Profile } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { Button, Field, Input, Select } from '@/components';
import { AuthShell } from '@/features/auth/AuthShell';

const STAGES = [['school', 'School'], ['undergraduate', 'Undergraduate'], ['postgraduate', 'Postgraduate'], ['professional', 'Working professional'], ['other', 'Other']];
const GOAL_TYPES = [['skill', 'Learn a skill'], ['exam', 'Prepare for an exam'], ['course', 'Finish a course'], ['project', 'Build a project'], ['custom', 'Something else']];

export function OnboardingPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [step, setStep] = useState<1 | 2>(1);
  const [profile, setProfile] = useState({ education_stage: 'undergraduate', college_name: '', college_year: '', branch: '', current_skill_level: 'beginner', preferred_pace: 'steady' });
  const [goal, setGoal] = useState({ title: '', goal_type: 'skill', weekly_hours: 8, target_date: '' });
  const saveProfile = useMutation({ mutationFn: (values: Partial<Profile>) => api<Profile>('/api/me/profile', { method: 'PATCH', json: values }), onSuccess: () => setStep(2) });
  const createGoal = useMutation({
    mutationFn: () => api<Goal>('/api/goals', { method: 'POST', json: { title: goal.title.trim(), goal_type: goal.goal_type, weekly_hours: Number(goal.weekly_hours), target_date: goal.target_date || null } }),
    onSuccess: async () => { await refresh(); navigate('/', { replace: true }); },
  });
  const err = (m: unknown) => (m instanceof ApiError ? m.message : undefined);

  if (step === 1) return (
    <AuthShell eyebrow="Step 1 of 2" title="Tell StudyOS where you are">
      <form className="grid gap-4" onSubmit={(e: FormEvent) => { e.preventDefault(); saveProfile.mutate(profile); }}>
        <Field label="Stage"><Select value={profile.education_stage} onChange={e => setProfile({ ...profile, education_stage: e.target.value })}>{STAGES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="College / school"><Input value={profile.college_name} onChange={e => setProfile({ ...profile, college_name: e.target.value })} /></Field>
          <Field label="Year"><Input value={profile.college_year} onChange={e => setProfile({ ...profile, college_year: e.target.value })} placeholder="2nd year" /></Field>
        </div>
        <Field label="Branch / field"><Input value={profile.branch} onChange={e => setProfile({ ...profile, branch: e.target.value })} placeholder="Computer Science" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Current level"><Select value={profile.current_skill_level} onChange={e => setProfile({ ...profile, current_skill_level: e.target.value })}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></Select></Field>
          <Field label="Pace"><Select value={profile.preferred_pace} onChange={e => setProfile({ ...profile, preferred_pace: e.target.value })}><option value="relaxed">Relaxed</option><option value="steady">Steady</option><option value="intense">Intense</option></Select></Field>
        </div>
        {err(saveProfile.error) && <p className="text-red text-[13px]">{err(saveProfile.error)}</p>}
        <div className="flex gap-2 justify-end"><Button type="button" variant="ghost" onClick={() => setStep(2)}>Skip for now</Button><Button type="submit" loading={saveProfile.isPending}>Continue</Button></div>
      </form>
    </AuthShell>
  );
  return (
    <AuthShell eyebrow="Step 2 of 2" title="What are you learning first?">
      <form className="grid gap-4" onSubmit={(e: FormEvent) => { e.preventDefault(); createGoal.mutate(); }}>
        <Field label="Goal title" hint="Be concrete: “Pass DBMS mid-sem”, “Learn PyTorch basics”"><Input value={goal.title} onChange={e => setGoal({ ...goal, title: e.target.value })} minLength={3} required /></Field>
        <Field label="Type"><Select value={goal.goal_type} onChange={e => setGoal({ ...goal, goal_type: e.target.value })}>{GOAL_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Hours per week"><Input type="number" min={1} max={80} value={goal.weekly_hours} onChange={e => setGoal({ ...goal, weekly_hours: Number(e.target.value) })} /></Field>
          <Field label="Target date (optional)"><Input type="date" value={goal.target_date} onChange={e => setGoal({ ...goal, target_date: e.target.value })} /></Field>
        </div>
        {err(createGoal.error) && <p className="text-red text-[13px]">{err(createGoal.error)}</p>}
        <div className="flex gap-2 justify-end"><Button type="button" variant="ghost" onClick={() => setStep(1)}>Back</Button><Button type="submit" loading={createGoal.isPending}>Create my plan</Button></div>
      </form>
    </AuthShell>
  );
}
