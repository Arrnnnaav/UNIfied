import { FormEvent, useState } from 'react';
import { Button, Card, EmptyState, Field, Input, Modal, PageHeader, Spinner, Tag, Textarea, useToast } from '@/components';
import { useDashboard } from '@/features/today/useDashboard';
import { Milestone, useMilestoneActions, useMilestones, useMilestoneShares } from './useMilestones';

export function MilestonesPage() {
  const milestones = useMilestones();
  const shares = useMilestoneShares();
  const dashboard = useDashboard();
  const { create, share } = useMilestoneActions();
  const { push } = useToast();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [shareTarget, setShareTarget] = useState<Milestone | null>(null);
  const [recipient, setRecipient] = useState('');
  const [message, setMessage] = useState('');

  const goalId = dashboard.data?.goal?.id;

  const submitCreate = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      { ...(goalId ? { goal_id: goalId } : {}), title: title.trim(), description: description.trim() },
      {
        onSuccess: () => { setTitle(''); setDescription(''); push('Milestone created'); },
        onError: err => push(err.message, 'error'),
      },
    );
  };

  const submitShare = (e: FormEvent) => {
    e.preventDefault();
    if (!shareTarget) return;
    share.mutate(
      { id: shareTarget.id, recipient_student_id: recipient.trim(), message: message.trim() },
      {
        onSuccess: () => { setShareTarget(null); setRecipient(''); setMessage(''); push('Milestone shared'); },
        onError: err => push(err.message, 'error'),
      },
    );
  };

  return (
    <>
      <PageHeader eyebrow="Milestones" title="Mark the moments that matter." subtitle="Achievements on your goal, shared with the people who keep you going." />

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card eyebrow="Your milestones" title={dashboard.data?.goal?.title || 'Milestones'}>
          {milestones.isPending ? <Spinner /> : milestones.error ? (
            <EmptyState title="Milestones unavailable" body={milestones.error.message} />
          ) : (milestones.data || []).length === 0 ? (
            <EmptyState title="No milestones yet" body="Create one below to mark a checkpoint on your goal." />
          ) : (
            <div className="grid gap-3">
              {(milestones.data || []).map(m => (
                <div key={m.id} className="flex items-center justify-between gap-4 border border-line p-3">
                  <div>
                    <p className="text-text">{m.title}</p>
                    {m.description && <p className="text-dim text-[13px] mt-0.5">{m.description}</p>}
                    <p className="font-mono text-muted text-[12px] mt-1">
                      {m.status === 'completed'
                        ? `achieved ${m.completed_at ? new Date(m.completed_at).toLocaleDateString() : ''}`
                        : `${Math.round(m.progress * 100)}% · ${m.status}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Tag tone={m.status === 'completed' ? 'accent' : 'muted'}>{m.status}</Tag>
                    <Button size="sm" variant="ghost" onClick={() => { setShareTarget(m); setRecipient(''); setMessage(''); }}>Share</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card eyebrow="Shared with you" title="Received milestones">
          {shares.isPending ? <Spinner /> : shares.error ? (
            <p className="text-muted text-[13px] py-6 text-center">Shares are unavailable.</p>
          ) : (shares.data || []).filter(s => s.direction === 'received').length === 0 ? (
            <p className="text-muted text-[13px] py-6 text-center">Nobody has shared a milestone with you yet.</p>
          ) : (
            <div className="grid gap-3">
              {(shares.data || []).filter(s => s.direction === 'received').map(s => (
                <div key={s.id} className="border border-line p-3">
                  <p className="text-text">{s.milestone?.title || 'Milestone'}</p>
                  {s.message && <p className="text-dim text-[13px] mt-0.5">“{s.message}”</p>}
                  <p className="font-mono text-muted text-[12px] mt-1">from {s.from_student_id} · {new Date(s.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card eyebrow="New milestone" title="Add a checkpoint">
        <form onSubmit={submitCreate} className="grid gap-4 max-w-lg">
          <Field label="Title"><Input aria-label="Milestone title" value={title} onChange={e => setTitle(e.target.value)} required /></Field>
          <Field label="Description"><Textarea aria-label="Milestone description" value={description} onChange={e => setDescription(e.target.value)} /></Field>
          <div><Button type="submit" loading={create.isPending} disabled={!title.trim()}>Create milestone</Button></div>
        </form>
      </Card>

      <Modal open={shareTarget !== null} title={`Share “${shareTarget?.title || ''}”`} onClose={() => setShareTarget(null)}>
        <form onSubmit={submitShare} className="grid gap-4">
          <Field label="Recipient student ID"><Input aria-label="Recipient student ID" value={recipient} onChange={e => setRecipient(e.target.value)} required placeholder="e.g. STU-001" /></Field>
          <Field label="Message"><Textarea aria-label="Share message" value={message} onChange={e => setMessage(e.target.value)} placeholder="Optional note" /></Field>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="ghost" onClick={() => setShareTarget(null)}>Cancel</Button>
            <Button type="submit" loading={share.isPending} disabled={!recipient.trim()}>Send share</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
