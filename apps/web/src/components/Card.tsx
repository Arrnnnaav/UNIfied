import { ReactNode } from 'react';
export function Card({ eyebrow, title, actions, children, className = '' }: { eyebrow?: string; title?: ReactNode; actions?: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <section className={`bg-surface border border-line shadow-card p-5 ${className}`}>
      {(eyebrow || title || actions) && (
        <header className="flex items-start justify-between gap-4 mb-4">
          <div>{eyebrow && <p className="label">{eyebrow}</p>}{title && <h2 className="text-xl mt-1">{title}</h2>}</div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
