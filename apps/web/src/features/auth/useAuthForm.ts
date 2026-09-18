import { useState } from 'react';
import { api, ApiError } from '@/api/client';
import type { AuthResponse } from '@/api/types';
import { setToken } from '@/auth/storage';

export function useAuthForm(path: '/api/auth/login' | '/api/auth/register', onDone: (auth: AuthResponse) => void) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(values: Record<string, string>) {
    setPending(true); setError(null);
    try { const auth = await api<AuthResponse>(path, { method: 'POST', json: values }); setToken(auth.access_token); onDone(auth); }
    catch (e) { setError(e instanceof ApiError ? e.message : 'Something went wrong'); }
    finally { setPending(false); }
  }
  return { submit, pending, error };
}
