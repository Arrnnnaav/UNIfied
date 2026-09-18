import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { Button, Field, Input } from '@/components';
import { AuthShell } from './AuthShell';
import { useAuthForm } from './useAuthForm';

export function RegisterPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [name, setName] = useState(''); const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const { submit, pending, error } = useAuthForm('/api/auth/register', async () => { await refresh(); navigate('/onboarding', { replace: true }); });
  const onSubmit = (e: FormEvent) => { e.preventDefault(); submit({ name, email, password }); };
  return (
    <AuthShell eyebrow="Account" title="Create your learning space" footer={<>Already have an account? <Link className="text-accent underline" to="/login">Sign in</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4">
        <Field label="Name"><Input value={name} onChange={e => setName(e.target.value)} autoComplete="name" required /></Field>
        <Field label="Email"><Input value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" required /></Field>
        <Field label="Password" hint="At least 8 characters" error={error || undefined}>
          <Input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="new-password" minLength={8} required />
        </Field>
        <Button type="submit" loading={pending}>Create account</Button>
      </form>
    </AuthShell>
  );
}
