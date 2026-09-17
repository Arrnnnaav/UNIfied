import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, setUnauthorizedHandler } from '@/api/client';
import type { Me } from '@/api/types';
import { clearToken, getToken } from './storage';

interface AuthState { me: Me | null; loading: boolean; error: ApiError | null; refresh: () => Promise<void>; signOut: () => void }
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const hasToken = Boolean(getToken());
  const query = useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/api/auth/me'), enabled: hasToken, retry: false });
  useEffect(() => { setUnauthorizedHandler(() => { client.setQueryData(['me'], null); client.removeQueries({ queryKey: ['me'] }); }); }, [client]);
  const refresh = useCallback(async () => { await client.invalidateQueries({ queryKey: ['me'] }); }, [client]);
  const signOut = useCallback(() => { clearToken(); client.clear(); window.location.assign('/login'); }, [client]);
  const value = useMemo<AuthState>(() => ({
    me: hasToken && !query.isError ? (query.data ?? null) : null,
    loading: hasToken && query.isPending,
    error: (query.error as ApiError) ?? null, refresh, signOut,
  }), [hasToken, query.data, query.isPending, query.isError, query.error, refresh, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth outside AuthProvider');
  return ctx;
}
