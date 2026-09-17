export function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return <div className="bg-surface2 border border-line p-4"><p className="label">{label}</p><p className="font-mono text-3xl mt-1 text-text">{value}</p>{hint && <p className="text-muted text-[12px] mt-1">{hint}</p>}</div>;
}
