import { createContext, ReactNode, useCallback, useContext, useState } from 'react';
type Toast = { id: number; message: string; kind: 'ok' | 'error' };
const Ctx = createContext<{ push: (message: string, kind?: 'ok' | 'error') => void } | null>(null);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((message: string, kind: 'ok' | 'error' = 'ok') => { const id = Date.now() + Math.random(); setItems(t => [...t, { id, message, kind }]); setTimeout(() => setItems(t => t.filter(i => i.id !== id)), 5000); }, []);
  return <Ctx.Provider value={{ push }}>{children}<div className="fixed bottom-4 right-4 z-50 grid gap-2">{items.map(t => <div key={t.id} role="alert" className={`px-4 py-2 border font-mono text-[13px] bg-surface ${t.kind === 'error' ? 'border-red text-red' : 'border-accent text-accent'}`}>{t.message}</div>)}</div></Ctx.Provider>;
}
export function useToast() { const ctx = useContext(Ctx); if (!ctx) throw new Error('useToast outside ToastProvider'); return ctx; }
