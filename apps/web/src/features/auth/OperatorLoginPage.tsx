import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { Button, Field, Input } from '@/components';
import { AuthShell } from './AuthShell';
import { useAuthForm } from './useAuthForm';

export function OperatorLoginPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const { submit, pending, error } = useAuthForm('/api/auth/login', async () => { await refresh(); navigate('/operator', { replace: true }); });
  const onSubmit = (e: FormEvent) => { e.preventDefault(); submit({ email, password }); };
  return (
    <AuthShell eyebrow="Operator" title="Operator sign-in" footer="Operators are created with the bootstrap token by an admin.">
      <form onSubmit={onSubmit} className="grid gap-4">
        <Field label="Email"><Input value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" required /></Field>
        <Field label="Password" error={error || undefined}><Input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required /></Field>
        <Button type="submit" loading={pending}>Sign in</Button>
      </form>
    </AuthShell>
  );
}
