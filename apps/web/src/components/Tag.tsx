import { ReactNode } from 'react';
const tones = { accent: 'bg-accent-tint text-accent', accent2: 'bg-accent2-tint text-accent2', muted: 'bg-surface3 text-dim', yellow: 'bg-yellow/15 text-yellow', red: 'bg-red/15 text-red' };
export function Tag({ tone = 'muted', children }: { tone?: keyof typeof tones; children: ReactNode }) {
  return <span className={`inline-block font-mono text-[11px] tracking-wide px-2 py-0.5 rounded ${tones[tone]}`}>{children}</span>;
}
