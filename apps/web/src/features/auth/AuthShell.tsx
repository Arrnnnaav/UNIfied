import { ReactNode } from 'react';
export function AuthShell({ eyebrow, title, children, footer }: { eyebrow: string; title: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="min-h-screen grid place-items-center p-6">
      <div className="w-full max-w-md">
        <div className="font-display text-3xl mb-6"><span className="text-accent">◒</span> StudyOS</div>
        <div className="bg-surface border border-line shadow-card p-6"><p className="label">{eyebrow}</p><h1 className="text-2xl mt-1 mb-5">{title}</h1>{children}</div>
        {footer && <p className="text-dim text-[13px] mt-4">{footer}</p>}
      </div>
    </div>
  );
}
