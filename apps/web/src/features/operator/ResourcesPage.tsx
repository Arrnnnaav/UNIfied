import { Button, Card, EmptyState, PageHeader, Spinner, Table, Tag } from '@/components';
import { useOperatorActions, useSnapshot } from './useOperator';

const trustTone = (s: string) => (s === 'verified' ? 'accent' : s === 'rejected' ? 'red' : 'yellow') as 'accent' | 'red' | 'yellow';

export function ResourcesPage() {
  const { data, isPending, error } = useSnapshot();
  const { setTrust, retryJob } = useOperatorActions();

  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error || !data) return <EmptyState title="Snapshot unavailable" body={error?.message} />;

  return (
    <>
      <PageHeader eyebrow="Operator" title="Resources & ingestion" subtitle="Trust review and pipeline health." />
      <Card eyebrow="Resources" title={`${data.resources.length} resources`} className="mb-6">
        <Table
          rows={data.resources}
          columns={[
            { key: 'title', header: 'Title' },
            { key: 'source_type', header: 'Source', render: r => <Tag tone="muted">{r.source_type}</Tag> },
            { key: 'status', header: 'Status' },
            { key: 'trust_status', header: 'Trust', render: r => <Tag tone={trustTone(r.trust_status)}>{r.trust_status}</Tag> },
            {
              key: 'actions', header: '', render: r => (
                <div className="flex gap-2">
                  {r.trust_status !== 'verified' && <Button size="sm" variant="ghost" onClick={() => setTrust.mutate({ id: r.id, status: 'verified' })} disabled={setTrust.isPending}>Verify</Button>}
                  {r.trust_status !== 'rejected' && <Button size="sm" variant="danger" onClick={() => setTrust.mutate({ id: r.id, status: 'rejected' })} disabled={setTrust.isPending}>Reject</Button>}
                  {r.trust_status !== 'unverified' && <Button size="sm" variant="ghost" onClick={() => setTrust.mutate({ id: r.id, status: 'unverified' })} disabled={setTrust.isPending}>Reset</Button>}
                </div>
              ),
            },
          ]}
        />
      </Card>
      <Card eyebrow="Ingestion" title="Jobs">
        <Table
          rows={data.ingestion_jobs}
          columns={[
            { key: 'kind', header: 'Kind' },
            { key: 'status', header: 'Status', render: j => <Tag tone={j.status === 'completed' ? 'accent' : j.status === 'failed' || j.status === 'retry_pending' ? 'red' : 'muted'}>{j.status}</Tag> },
            { key: 'progress', header: 'Progress', render: j => <span className="font-mono text-[12px]">{Math.round(j.progress)}%</span> },
            { key: 'error', header: 'Error', render: j => <span className="text-red text-[12px]">{j.error || ''}</span> },
            {
              key: 'actions', header: '', render: j => (
                (j.status === 'failed' || j.status === 'retry_pending')
                  ? <Button size="sm" variant="ghost" onClick={() => retryJob.mutate(j.id)} disabled={retryJob.isPending}>Retry</Button>
                  : null
              ),
            },
          ]}
        />
      </Card>
    </>
  );
}
