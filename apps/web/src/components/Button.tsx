import { ButtonHTMLAttributes } from 'react';
type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger'; size?: 'sm' | 'md'; loading?: boolean };
const styles = { primary: 'bg-accent text-bg hover:bg-accent-strong', ghost: 'bg-transparent border border-strong text-text hover:bg-surface2', danger: 'bg-transparent border border-red text-red hover:bg-red/10' };
export function Button({ variant = 'primary', size = 'md', loading, className = '', children, disabled, ...rest }: Props) {
  return (
    <button {...rest} disabled={disabled || loading} className={`inline-flex items-center gap-2 font-semibold rounded transition ${size === 'sm' ? 'px-3 py-1.5 text-[13px]' : 'px-4 py-2 text-[14px]'} disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}>
      {loading ? <span className="animate-pulse">…</span> : null}{children}
    </button>
  );
}
