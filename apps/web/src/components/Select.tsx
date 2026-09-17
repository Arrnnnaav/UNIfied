import { SelectHTMLAttributes } from 'react';
import { inputClass } from './Field';
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) { return <select {...props} className={`${inputClass} ${props.className || ''}`} />; }
