import { ReactNode } from 'react';
export function EmptyState({ title, body, action }: { title: string; body?: string; action?: ReactNode }) {
  return <div className="border border-dashed border-strong p-8 text-center"><h3 className="text-lg">{title}</h3>{body && <p className="text-dim mt-1">{body}</p>}{action && <div className="mt-4 inline-flex">{action}</div>}</div>;
}
