import { ReactNode } from 'react';
export function PageHeader({ eyebrow, title, subtitle, actions }: { eyebrow: string; title: string; subtitle?: string; actions?: ReactNode }) {
  return <header className="flex items-end justify-between gap-4 mb-6 pb-4 rule"><div><p className="label">{eyebrow}</p><h1 className="text-3xl mt-1">{title}</h1>{subtitle && <p className="text-dim mt-1">{subtitle}</p>}</div>{actions && <div className="flex gap-2">{actions}</div>}</header>;
}
