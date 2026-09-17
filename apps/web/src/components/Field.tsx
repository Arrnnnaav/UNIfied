import { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react';
export const inputClass = 'w-full bg-bg border border-strong rounded px-3 py-2 text-text placeholder:text-muted focus:border-accent';
export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) {
  return <label className="block"><span className="label">{label}</span><div className="mt-1">{children}</div>{error ? <p className="text-red text-[12px] mt-1">{error}</p> : hint ? <p className="text-muted text-[12px] mt-1">{hint}</p> : null}</label>;
}
export function Input(props: InputHTMLAttributes<HTMLInputElement>) { return <input {...props} className={`${inputClass} ${props.className || ''}`} />; }
export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) { return <textarea {...props} className={`${inputClass} min-h-[90px] ${props.className || ''}`} />; }
