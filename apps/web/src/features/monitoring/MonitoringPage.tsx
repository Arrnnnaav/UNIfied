import { FormEvent, useState } from 'react';
import { Button, Card, EmptyState, Field, Input, PageHeader, Spinner, Table, Tag, useToast } from '@/components';
import { MonitoringStudent, useMonitoringActions, useMonitoringDashboard, useMonitoringDashboards } from './useMonitoring';

export function MonitoringPage() {
  const dashboards = useMonitoringDashboards();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detail = useMonitoringDashboard(selectedId);
  const { join } = useMonitoringActions();
  const { push } = useToast();
  const [code, setCode] = useState('');

  const submitJoin = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) return;
    join.mutate(trimmed, {
      onSuccess: () => { setCode(''); push('Joined dashboard'); },
      onError: err => push(err.message, 'error'),
    });
  };

  const pct = (v: number) => `${Math.round(v * 100)}%`;

  return (
    <>
      <PageHeader eyebrow="Monitoring" title="Stay accountable, together." subtitle="Join a mentor dashboard or keep an eye on the ones you lead." />

      <Card eyebrow="Join" title="Join a monitoring dashboard" className="mb-6">
        <form onSubmit={submitJoin} className="flex items-end gap-3 max-w-md">
          <div className="flex-1">
            <Field label="Access code"><Input aria-label="Access code" value={code} onChange={e => setCode(e.target.value)} placeholder="e.g. MON-ABC123" /></Field>
          </div>
          <Button type="submit" loading={join.isPending} disabled={!code.trim()}>Join</Button>
        </form>
      </Card>

      <Card eyebrow="Dashboards" title="Your dashboards" className="mb-6">
        {dashboards.isPending ? <Spinner /> : dashboards.error ? (
          <EmptyState title="Dashboards unavailable" body={dashboards.error.message} />
        ) : (
          <Table
            rows={(dashboards.data || []).map(d => ({ ...d, onSelect: () => setSelectedId(d.id) }))}
            empty="You are not part of any monitoring dashboard yet."
            columns={[
              { key: 'name', header: 'Name' },
              { key: 'status', header: 'Status', render: d => <Tag tone={d.status === 'active' ? 'accent' : 'muted'}>{d.status}</Tag> },
              { key: 'student_count', header: 'Students' },
              { key: 'open', header: '', render: d => <Button size="sm" variant="ghost" onClick={d.onSelect}>Open</Button> },
            ]}
          />
        )}
      </Card>

      {selectedId && (
        <Card eyebrow="Dashboard" title={detail.data?.name || 'Members'}>
          {detail.isPending ? <Spinner /> : detail.error ? (
            <EmptyState title="Dashboard unavailable" body={detail.error.message} />
          ) : (
            <Table<MonitoringStudent & { id: string }>
              rows={(detail.data?.students || []).map((s, i) => ({ ...s, id: s.student_id || String(i) }))}
              empty="No members yet."
              columns={[
                { key: 'student_id', header: 'Student ID' },
                { key: 'name', header: 'Name' },
                { key: 'average_mastery', header: 'Mastery', render: s => pct(s.average_mastery) },
                { key: 'session_minutes', header: 'Minutes' },
                { key: 'on_track', header: 'On track', render: s => <Tag tone={s.on_track ? 'accent' : 'yellow'}>{s.on_track ? 'on track' : 'needs nudge'}</Tag> },
              ]}
            />
          )}
        </Card>
      )}
    </>
  );
}
