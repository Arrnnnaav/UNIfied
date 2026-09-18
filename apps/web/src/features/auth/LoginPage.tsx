import { FormEvent, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { Button, Field, Input } from '@/components';
import { AuthShell } from './AuthShell';
import { useAuthForm } from './useAuthForm';

export function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { refresh } = useAuth();
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const { submit, pending, error } = useAuthForm('/api/auth/login', async () => { await refresh(); navigate(params.get('next') || '/', { replace: true }); });
  const onSubmit = (e: FormEvent) => { e.preventDefault(); submit({ email, password }); };
  return (
    <AuthShell eyebrow="Account" title="Sign in to your learning space" footer={<>New here? <Link className="text-accent underline" to="/register">Create an account</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4">
        <Field label="Email or StudyOS ID"><Input value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" required /></Field>
        <Field label="Password" error={error || undefined}><Input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required /></Field>
        <Button type="submit" loading={pending}>Sign in</Button>
      </form>
    </AuthShell>
  );
}
