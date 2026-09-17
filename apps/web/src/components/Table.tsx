import { ReactNode } from 'react';
export interface Column<Row> { key: string; header: string; render?: (row: Row) => ReactNode; className?: string }
export function Table<Row extends Record<string, any>>({ columns, rows, empty = 'Nothing here yet.', rowKey = (r: Row) => String(r.id) }: { columns: Column<Row>[]; rows: Row[]; empty?: string; rowKey?: (r: Row) => string }) {
  if (!rows.length) return <p className="text-muted text-[13px] py-6 text-center">{empty}</p>;
  return (
    <div className="overflow-x-auto"><table className="w-full text-[14px]">
      <thead><tr className="rule">{columns.map(c => <th key={c.key} className={`label text-left py-2 pr-4 ${c.className || ''}`}>{c.header}</th>)}</tr></thead>
      <tbody>{rows.map(r => <tr key={rowKey(r)} className="border-b border-line">{columns.map(c => <td key={c.key} className={`py-2 pr-4 align-top ${c.className || ''}`}>{c.render ? c.render(r) : String(r[c.key] ?? '')}</td>)}</tr>)}</tbody>
    </table></div>
  );
}
