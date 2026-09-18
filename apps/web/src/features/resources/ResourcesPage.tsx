import { FormEvent, useState } from 'react';
import { Button, Card, EmptyState, Field, Input, PageHeader, Spinner, Table, Tag, Textarea } from '@/components';
import { useDashboard } from '../today/useDashboard';
import { Resource, useIngestionJobs, useResourceActions, useSearch } from './useResources';

type Tab = 'text' | 'url' | 'github' | 'youtube' | 'upload';

const tabs: { key: Tab; label: string }[] = [
  { key: 'text', label: 'Paste text' },
  { key: 'url', label: 'URL' },
  { key: 'github', label: 'GitHub' },
  { key: 'youtube', label: 'YouTube' },
  { key: 'upload', label: 'Upload file' },
];

const trustTone = (trust: string) => (trust === 'verified' ? 'accent' : trust === 'rejected' ? 'red' : 'yellow') as 'accent' | 'red' | 'yellow';

function AddMaterial({ goalId }: { goalId: string }) {
  const [tab, setTab] = useState<Tab>('text');
  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');
  const [content, setContent] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const { createResource, ingest, upload } = useResourceActions(goalId);
  const busy = createResource.isPending || ingest.isPending || upload.isPending;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (tab === 'upload') {
        if (!file) { setError('Choose a file first.'); return; }
        await upload.mutateAsync({ file, title: title || file.name });
      } else if (tab === 'text') {
        await createResource.mutateAsync({ goal_id: goalId, title, source_type: 'text', content });
      } else {
        const resource = await createResource.mutateAsync({ goal_id: goalId, title, source_type: tab, url });
        await ingest.mutateAsync({ id: resource.id, kind: tab, url });
      }
      setTitle(''); setUrl(''); setContent(''); setFile(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Card eyebrow="Add material" title="Bring sources into your library">
      <div className="flex flex-wrap gap-2 mb-4">
        {tabs.map(t => (
          <Button key={t.key} size="sm" variant={tab === t.key ? 'primary' : 'ghost'} onClick={() => setTab(t.key)}>{t.label}</Button>
        ))}
      </div>
      <form onSubmit={submit} className="grid gap-3">
        <Field label="Title"><Input value={title} onChange={e => setTitle(e.target.value)} required={tab !== 'upload'} /></Field>
        {tab === 'text' && <Field label="Content"><Textarea value={content} onChange={e => setContent(e.target.value)} required /></Field>}
        {(tab === 'url' || tab === 'github' || tab === 'youtube') && (
          <Field label="URL"><Input type="url" value={url} onChange={e => setUrl(e.target.value)} required /></Field>
        )}
        {tab === 'upload' && <Field label="File"><Input type="file" onChange={e => setFile(e.target.files?.[0] ?? null)} required /></Field>}
        {error && <p className="text-red text-[13px]">{error}</p>}
        <div><Button size="sm" type="submit" loading={busy}>{tab === 'upload' ? 'Upload' : 'Add'}</Button></div>
      </form>
    </Card>
  );
}

export function ResourcesPage() {
  const { data, isPending, error } = useDashboard();
  const jobs = useIngestionJobs();
  const [q, setQ] = useState('');
  const goalId = data?.goal?.id;
  const search = useSearch(q, goalId);

  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error) return <EmptyState title="Resources are unavailable" body={error.message} />;
  if (!data?.goal) return <EmptyState title="No goal yet" body="Create a goal before adding resources." />;

  const resources = (data.goal.resources || []) as Resource[];

  return (
    <>
      <PageHeader eyebrow="Resources" title="Resources" subtitle="Materials, ingestion and search for your goal." />
      <div className="grid grid-cols-2 gap-4 mb-6">
        <AddMaterial goalId={data.goal.id} />
        <Card eyebrow="Your library" title="Materials">
          <Table<Resource>
            rows={resources}
            empty="No resources yet. Add your first material."
            columns={[
              { key: 'title', header: 'Title' },
              { key: 'source_type', header: 'Type', render: r => <Tag tone="muted">{r.source_type}</Tag> },
              { key: 'status', header: 'Status' },
              { key: 'trust_status', header: 'Trust', render: r => <Tag tone={trustTone(r.trust_status)}>{r.trust_status}</Tag> },
            ]}
          />
        </Card>
      </div>
      <Card eyebrow="Ingestion" title="Jobs" className="mb-6">
        {jobs.isPending ? <Spinner /> : (jobs.data || []).length === 0 ? (
          <p className="text-dim text-[13px]">No ingestion jobs yet.</p>
        ) : (
          <div className="grid gap-3">
            {(jobs.data || []).map(job => (
              <div key={job.id} className="border border-line p-3">
                <div className="flex items-center justify-between gap-4 mb-2">
                  <p className="text-text">{job.kind}</p>
                  <Tag tone={job.status === 'failed' ? 'red' : job.status === 'done' ? 'accent' : 'yellow'}>{job.status}</Tag>
                </div>
                <div className="h-1.5 bg-surface3 rounded">
                  <div className="h-full bg-accent rounded" style={{ width: `${Math.round(job.progress * 100)}%` }} />
                </div>
                {job.error && <p className="text-red text-[13px] mt-2">{job.error}</p>}
              </div>
            ))}
          </div>
        )}
      </Card>
      <Card eyebrow="Search" title="Find in your materials">
        <Field label="Query">
          <Input value={q} onChange={e => setQ(e.target.value)} placeholder="Search your resources…" />
        </Field>
        {q.trim().length > 0 && (
          <div className="grid gap-3 mt-4">
            {search.isPending ? <Spinner /> : (search.data || []).length === 0 ? (
              <p className="text-dim text-[13px]">No matches.</p>
            ) : (
              (search.data || []).map((r, i) => (
                <div key={`${r.resource_id}-${i}`} className="border border-line p-3">
                  <p className="text-text">{r.title}</p>
                  <p className="text-dim text-[13px] mt-0.5">{r.snippet}</p>
                </div>
              ))
            )}
          </div>
        )}
      </Card>
    </>
  );
}
