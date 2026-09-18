import { Card, EmptyState, PageHeader, Spinner, Table, Tag } from '@/components';
import { useSnapshot } from './useOperator';

export function UsersPage() {
  const { data, isPending, error } = useSnapshot();
  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error || !data) return <EmptyState title="Snapshot unavailable" body={error?.message} />;

  return (
    <>
      <PageHeader eyebrow="Operator" title="Users & activity" subtitle="Accounts, goals and the audit trail." />
      <Card eyebrow="Users" title={`${data.users.length} accounts`} className="mb-6">
        <Table
          rows={data.users}
          columns={[
            { key: 'name', header: 'Name' },
            { key: 'role', header: 'Role', render: u => <Tag tone={u.role === 'operator' ? 'accent2' : 'muted'}>{u.role}</Tag> },
            { key: 'created_at', header: 'Created', render: u => new Date(u.created_at).toLocaleDateString() },
          ]}
        />
      </Card>
      <Card eyebrow="Goals" title={`${data.goals.length} goals`} className="mb-6">
        <Table
          rows={data.goals}
          columns={[
            { key: 'title', header: 'Title' },
            { key: 'status', header: 'Status', render: g => <Tag tone={g.status === 'active' ? 'accent' : 'muted'}>{g.status}</Tag> },
            { key: 'topics', header: 'Topics' },
            { key: 'resources', header: 'Resources' },
          ]}
        />
      </Card>
      <Card eyebrow="Audit log" title="Recent operator-visible actions">
        <Table
          rows={data.audit_log}
          columns={[
            { key: 'action', header: 'Action', render: a => <span className="font-mono text-[12px]">{a.action}</span> },
            { key: 'entity_type', header: 'Entity', render: a => `${a.entity_type} ${a.entity_id}` },
            { key: 'created_at', header: 'When', render: a => new Date(a.created_at).toLocaleString() },
          ]}
        />
      </Card>
    </>
  );
}
