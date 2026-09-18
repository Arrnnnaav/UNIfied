import { FormEvent, useEffect, useState } from 'react';
import { apiBase } from '@/api/client';
import { getToken } from '@/auth/storage';
import { useAuth } from '@/auth/AuthProvider';
import { Button, Card, EmptyState, Field, Input, Modal, PageHeader, Select, Spinner, Textarea, useToast } from '@/components';
import { useProfile, useProfileActions } from './useProfile';

const STAGES = ['school', 'undergraduate', 'postgraduate', 'working', 'other'];
const LEVELS = ['beginner', 'intermediate', 'advanced'];
const PACES = ['slow', 'steady', 'fast'];
const MODES = ['text', 'video', 'practice', 'projects'];

const emptyForm = {
  education_stage: 'other',
  graduation_year: '',
  current_skill_level: 'beginner',
  learning_modes: [] as string[],
  preferred_pace: 'steady',
  known_skills: '',
  constraints: '',
  college_name: '',
  college_year: '',
  branch: '',
  college_id: '',
};

export function ProfilePage() {
  const { data, isPending, error } = useProfile();
  const { update, deleteAccount } = useProfileActions();
  const { signOut } = useAuth();
  const { push } = useToast();
  const [form, setForm] = useState(emptyForm);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState('');

  useEffect(() => {
    if (!data) return;
    setForm({
      education_stage: data.education_stage || 'other',
      graduation_year: data.graduation_year ? String(data.graduation_year) : '',
      current_skill_level: data.current_skill_level || 'beginner',
      learning_modes: data.learning_modes || [],
      preferred_pace: data.preferred_pace || 'steady',
      known_skills: (data.known_skills || []).join(', '),
      constraints: data.constraints || '',
      college_name: data.college_name || '',
      college_year: data.college_year || '',
      branch: data.branch || '',
      college_id: data.college_id || '',
    });
  }, [data]);

  const set = (patch: Partial<typeof emptyForm>) => setForm(f => ({ ...f, ...patch }));

  const toggleMode = (mode: string) =>
    set({ learning_modes: form.learning_modes.includes(mode) ? form.learning_modes.filter(m => m !== mode) : [...form.learning_modes, mode] });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    update.mutate(
      {
        education_stage: form.education_stage,
        graduation_year: form.graduation_year ? Number(form.graduation_year) : null,
        current_skill_level: form.current_skill_level,
        known_skills: form.known_skills.split(',').map(s => s.trim()).filter(Boolean),
        learning_modes: form.learning_modes,
        preferred_pace: form.preferred_pace,
        constraints: form.constraints,
        college_name: form.college_name,
        college_year: form.college_year,
        branch: form.branch,
        college_id: form.college_id,
        coding_profiles: data?.coding_profiles || {},
      },
      { onSuccess: () => push('Profile saved'), onError: err => push(err.message, 'error') },
    );
  };

  const exportData = async () => {
    try {
      const headers: Record<string, string> = {};
      const token = getToken();
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await fetch(`${apiBase()}/api/me/export`, { headers });
      if (!res.ok) throw new Error(`export failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'studyos-export.json';
      a.click();
      URL.revokeObjectURL(url);
      push('Export downloaded');
    } catch (err) {
      push((err as Error).message, 'error');
    }
  };

  const confirmDelete = () => {
    deleteAccount.mutate(undefined, { onSuccess: () => signOut(), onError: err => push(err.message, 'error') });
  };

  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error) return <EmptyState title="Profile unavailable" body={error.message} />;

  return (
    <>
      <PageHeader eyebrow="Profile" title="Tune StudyOS to you." subtitle={data?.email ? `${data.name} · ${data.email}${data.student_id ? ` · ${data.student_id}` : ''}` : undefined} />

      <Card eyebrow="Learning profile" title="About you" className="mb-6">
        <form onSubmit={submit} className="grid grid-cols-2 gap-4">
          <Field label="Education stage">
            <Select aria-label="Education stage" value={form.education_stage} onChange={e => set({ education_stage: e.target.value })}>
              {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
            </Select>
          </Field>
          <Field label="Graduation year">
            <Input aria-label="Graduation year" type="number" value={form.graduation_year} onChange={e => set({ graduation_year: e.target.value })} />
          </Field>
          <Field label="Current skill level">
            <Select aria-label="Current skill level" value={form.current_skill_level} onChange={e => set({ current_skill_level: e.target.value })}>
              {LEVELS.map(s => <option key={s} value={s}>{s}</option>)}
            </Select>
          </Field>
          <Field label="Preferred pace">
            <Select aria-label="Preferred pace" value={form.preferred_pace} onChange={e => set({ preferred_pace: e.target.value })}>
              {PACES.map(s => <option key={s} value={s}>{s}</option>)}
            </Select>
          </Field>
          <Field label="Learning modes">
            <div className="flex flex-wrap gap-4 pt-2">
              {MODES.map(mode => (
                <label key={mode} className="flex items-center gap-2 text-text text-[14px]">
                  <input type="checkbox" aria-label={`Learning mode: ${mode}`} checked={form.learning_modes.includes(mode)} onChange={() => toggleMode(mode)} />
                  {mode}
                </label>
              ))}
            </div>
          </Field>
          <Field label="Known skills" hint="Comma separated.">
            <Input aria-label="Known skills" value={form.known_skills} onChange={e => set({ known_skills: e.target.value })} placeholder="python, calculus" />
          </Field>
          <Field label="Constraints">
            <Textarea aria-label="Constraints" value={form.constraints} onChange={e => set({ constraints: e.target.value })} />
          </Field>
          <Field label="College name"><Input aria-label="College name" value={form.college_name} onChange={e => set({ college_name: e.target.value })} /></Field>
          <Field label="College year"><Input aria-label="College year" value={form.college_year} onChange={e => set({ college_year: e.target.value })} /></Field>
          <Field label="Branch"><Input aria-label="Branch" value={form.branch} onChange={e => set({ branch: e.target.value })} /></Field>
          <Field label="College ID"><Input aria-label="College ID" value={form.college_id} onChange={e => set({ college_id: e.target.value })} /></Field>
          <div className="col-span-2">
            <Button type="submit" loading={update.isPending}>Save profile</Button>
          </div>
        </form>
      </Card>

      <Card eyebrow="Data & privacy" title="Your data">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <p className="text-dim text-[13px]">Download everything StudyOS holds about you, or permanently delete your account.</p>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={exportData}>Export my data</Button>
            <Button variant="danger" onClick={() => { setConfirmText(''); setConfirmOpen(true); }}>Delete account</Button>
          </div>
        </div>
      </Card>

      <Modal open={confirmOpen} title="Delete account" onClose={() => setConfirmOpen(false)}>
        <p className="text-dim text-[13px] mb-4">This permanently deletes your account and learning data. Type <span className="font-mono text-red">DELETE</span> to confirm.</p>
        <Field label="Confirm"><Input aria-label="Type DELETE to confirm" value={confirmText} onChange={e => setConfirmText(e.target.value)} /></Field>
        <div className="flex gap-2 justify-end mt-4">
          <Button variant="ghost" onClick={() => setConfirmOpen(false)}>Cancel</Button>
          <Button variant="danger" disabled={confirmText !== 'DELETE'} loading={deleteAccount.isPending} onClick={confirmDelete}>Delete my account</Button>
        </div>
      </Modal>
    </>
  );
}
