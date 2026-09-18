import { FormEvent, useState } from 'react';
import { Button, Card, EmptyState, Field, Input, PageHeader, Select, Spinner, Table, Tag, useToast } from '@/components';
import { useOperatorActions, useSnapshot } from './useOperator';

export function MonitoringPage() {
  const { data, isPending, error } = useSnapshot();
  const { createDashboard, enroll } = useOperatorActions();
  const { push } = useToast();
  const [name, setName] = useState('');
  const [leaderId, setLeaderId] = useState('');
  const [dashboardId, setDashboardId] = useState('');
  const [studentId, setStudentId] = useState('');

  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error || !data) return <EmptyState title="Monitoring unavailable" body={error?.message} />;

  const dashboards = data.monitoring_dashboards;
  const selected = dashboardId || dashboards[0]?.id || '';

  const submitCreate = (e: FormEvent) => {
    e.preventDefault();
    createDashboard.mutate({ name, leader_student_id: leaderId }, {
      onSuccess: () => { push('Dashboard created'); setName(''); setLeaderId(''); },
      onError: err => push(err.message, 'error'),
    });
  };
  const submitEnroll = (e: FormEvent) => {
    e.preventDefault();
    enroll.mutate({ id: selected, student_id: studentId }, {
      onSuccess: () => { push('Student enrolled'); setStudentId(''); },
      onError: err => push(err.message, 'error'),
    });
  };

  return (
    <>
      <PageHeader eyebrow="Operator" title="Monitoring dashboards" subtitle="Create parent/mentor dashboards and enroll students." />
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card eyebrow="Create" title="New dashboard">
          <form onSubmit={submitCreate} className="grid gap-4">
            <Field label="Name"><Input value={name} onChange={e => setName(e.target.value)} required /></Field>
            <Field label="Leader student ID" hint="Student code of the dashboard leader, e.g. STU-1234"><Input value={leaderId} onChange={e => setLeaderId(e.target.value)} required /></Field>
            <Button type="submit" loading={createDashboard.isPending}>Create dashboard</Button>
          </form>
        </Card>
        <Card eyebrow="Enroll" title="Add a student">
          <form onSubmit={submitEnroll} className="grid gap-4">
            <Field label="Dashboard">
              <Select value={selected} onChange={e => setDashboardId(e.target.value)}>
                {dashboards.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </Select>
            </Field>
            <Field label="Student ID"><Input value={studentId} onChange={e => setStudentId(e.target.value)} required /></Field>
            <Button type="submit" loading={enroll.isPending} disabled={!selected}>Enroll student</Button>
          </form>
        </Card>
      </div>
      <Card eyebrow="Dashboards" title={`${dashboards.length} dashboards`}>
        <Table
          rows={dashboards}
          empty="No dashboards yet."
          columns={[
            { key: 'name', header: 'Name' },
            { key: 'status', header: 'Status', render: d => <Tag tone={d.status === 'active' ? 'accent' : 'muted'}>{d.status}</Tag> },
            { key: 'access_code', header: 'Access code', render: d => <span className="font-mono text-[12px]">{d.access_code}</span> },
          ]}
        />
      </Card>
    </>
  );
}
