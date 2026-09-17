import { ReactNode, useEffect } from 'react';
export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => { if (!open) return; const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose(); window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey); }, [open, onClose]);
  if (!open) return null;
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}><div role="dialog" aria-label={title} className="bg-surface border border-strong shadow-card p-6 w-full max-w-lg" onClick={e => e.stopPropagation()}><h2 className="text-xl mb-4">{title}</h2>{children}</div></div>;
}
