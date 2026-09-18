import { ChangeEvent, FormEvent, useRef, useState } from 'react';
import { Button, Card, EmptyState, Field, Input, Modal, PageHeader, Spinner, Table, Tag, Textarea, useToast } from '@/components';
import { useOperatorActions, useSnapshot } from './useOperator';

const statusTone = (s: string) => (s === 'published' ? 'accent' : s === 'archived' ? 'muted' : 'yellow') as 'accent' | 'muted' | 'yellow';

export function PackagesPage() {
  const { data, isPending, error } = useSnapshot();
  const { createPackage, uploadPackage, setPackageStatus } = useOperatorActions();
  const { push } = useToast();
  const [open, setOpen] = useState(false);
  const [slug, setSlug] = useState('');
  const [title, setTitle] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [manifest, setManifest] = useState('{}');
  const fileRef = useRef<HTMLInputElement>(null);

  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error || !data) return <EmptyState title="Packages unavailable" body={error?.message} />;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    let parsed: Record<string, unknown>;
    try { parsed = JSON.parse(manifest || '{}'); } catch { push('Manifest must be valid JSON', 'error'); return; }
    createPackage.mutate({ slug, title, version, manifest: parsed }, {
      onSuccess: () => { push('Package created'); setOpen(false); setSlug(''); setTitle(''); setVersion('1.0.0'); setManifest('{}'); },
      onError: err => push(err.message, 'error'),
    });
  };

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    uploadPackage.mutate(file, {
      onSuccess: () => push('Package uploaded'),
      onError: err => push(err.message, 'error'),
    });
    e.target.value = '';
  };

  return (
    <>
      <PageHeader
        eyebrow="Operator" title="Learning packages" subtitle="Versioned content bundles for goals."
        actions={<>
          <input ref={fileRef} type="file" accept=".json,.zip,application/json" className="hidden" data-testid="package-file" onChange={onFile} />
          <Button variant="ghost" onClick={() => fileRef.current?.click()} loading={uploadPackage.isPending}>Upload package</Button>
          <Button onClick={() => setOpen(true)}>New package</Button>
        </>}
      />
      <Card>
        <Table
          rows={data.packages}
          empty="No packages yet."
          columns={[
            { key: 'slug', header: 'Slug', render: p => <span className="font-mono text-[12px]">{p.slug}</span> },
            { key: 'title', header: 'Title' },
            { key: 'version', header: 'Version', render: p => <span className="font-mono text-[12px]">{p.version}</span> },
            { key: 'status', header: 'Status', render: p => <Tag tone={statusTone(p.status)}>{p.status}</Tag> },
            {
              key: 'actions', header: '', render: p => (
                <div className="flex gap-2">
                  {p.status !== 'published' && <Button size="sm" variant="ghost" onClick={() => setPackageStatus.mutate({ id: p.id, status: 'published' })} disabled={setPackageStatus.isPending}>Publish</Button>}
                  {p.status !== 'archived' && <Button size="sm" variant="danger" onClick={() => setPackageStatus.mutate({ id: p.id, status: 'archived' })} disabled={setPackageStatus.isPending}>Archive</Button>}
                </div>
              ),
            },
          ]}
        />
      </Card>
      <Modal open={open} title="New package" onClose={() => setOpen(false)}>
        <form onSubmit={submit} className="grid gap-4">
          <Field label="Slug" hint="lowercase, e.g. linear-algebra-core"><Input value={slug} onChange={e => setSlug(e.target.value)} required /></Field>
          <Field label="Title"><Input value={title} onChange={e => setTitle(e.target.value)} required /></Field>
          <Field label="Version"><Input value={version} onChange={e => setVersion(e.target.value)} required /></Field>
          <Field label="Manifest (JSON)"><Textarea value={manifest} onChange={e => setManifest(e.target.value)} /></Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createPackage.isPending}>Create</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
