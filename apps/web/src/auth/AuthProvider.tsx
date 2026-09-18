import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, setUnauthorizedHandler } from '@/api/client';
import type { Me } from '@/api/types';
import { clearToken, getToken } from './storage';

interface AuthState { me: Me | null; loading: boolean; error: ApiError | null; refresh: () => Promise<void>; signOut: () => void }
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  // `rev` bumps whenever sessions change so `getToken()` is re-read with the *new* value the render
  // after login/storage changes. Without this, login navigated with the provider still believing
  // there was no token, and the guard bounced back to /login?next=... (the "stuck" loop).
  const [rev, setRev] = useState(0);
  const token = getToken();
  const query = useQuery({
    queryKey: ['me', token, rev],
    queryFn: () => (token ? api<Me>('/api/auth/me') : Promise.resolve(null)),
    retry: false,
    staleTime: 30_000,
  });
  useEffect(() => { setUnauthorizedHandler(() => { client.clear(); setRev(r => r + 1); }); }, [client]);
  const refresh = useCallback(async () => { setRev(r => r + 1); await client.invalidateQueries({ queryKey: ['me'] }); }, [client]);
  const signOut = useCallback(() => { clearToken(); client.clear(); window.location.assign('/login'); }, [client]);
  const value = useMemo<AuthState>(() => ({
    me: token && !query.isError ? (query.data ?? null) : null,
    loading: Boolean(token) && query.isPending,
    error: (query.error as ApiError) ?? null, refresh, signOut,
  }), [token, query.data, query.isPending, query.isError, query.error, refresh, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth outside AuthProvider');
  return ctx;
}
