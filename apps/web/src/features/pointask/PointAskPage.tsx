import { Link } from 'react-router-dom';
import { Button, Card, EmptyState, PageHeader, Spinner, Tag } from '@/components';
import type { SpatialContext } from '@/api/types';
import { useQuizLater, useSpatial } from './useSpatial';
import { useExtensionDetect } from './useExtensionDetect';

function ExtensionCard({ version }: { version: string | null }) {
  if (version) {
    return (
      <Card eyebrow="Browser extension" title="Ready to point" className="mb-6">
        <p className="text-text">Extension installed (v{version}). Press <span className="font-mono">Alt+Shift+A</span> on any page or PDF.</p>
      </Card>
    );
  }
  return (
    <Card eyebrow="Browser extension" title="Install Point & Ask" className="mb-6">
      <ol className="grid gap-3 list-decimal list-inside text-text">
        <li>
          Install StudyOS Point &amp; Ask from the{' '}
          <a className="text-accent underline" href="https://chrome.google.com/webstore" target="_blank" rel="noreferrer">Chrome Web Store</a>
          {' '}(or chrome://extensions → Developer mode → Load unpacked → apps/extension).
        </li>
        <li>Press <span className="font-mono">Alt+Shift+A</span> on any page or PDF to mark a region and ask.</li>
        <li>Reload this page after installing so the extension can introduce itself.</li>
      </ol>
    </Card>
  );
}

function MetaLine({ mark }: { mark: SpatialContext }) {
  const parts: string[] = [];
  if (mark.turns > 1) parts.push(`${mark.turns} turns`);
  parts.push(`${Math.round(mark.confidence * 100)}% confidence`);
  const provider = mark.answer.meta?.provider;
  const model = mark.answer.meta?.model;
  if (provider || model) parts.push([provider, model].filter(Boolean).join('/'));
  const anchors = mark.answer.anchors_used?.length ?? 0;
  parts.push(`${anchors} anchors`);
  if (mark.review_status !== 'pending') parts.push(mark.review_status);
  return <p className="text-dim text-[13px] mt-1">{parts.join(' · ')}</p>;
}

function MarkRow({ mark }: { mark: SpatialContext }) {
  const quiz = useQuizLater();
  const due = quiz.data?.due_at ? new Date(quiz.data.due_at).toLocaleDateString() : '';
  return (
    <div className="border border-line p-3">
      <div className="flex items-center gap-3 flex-wrap">
        <Tag tone="accent2">{mark.page.surface}</Tag>
        {mark.page.url ? (
          <a className="text-accent underline" href={mark.page.url} target="_blank" rel="noreferrer">{mark.page.title}</a>
        ) : (
          <p className="text-text">{mark.page.title}</p>
        )}
      </div>
      <p className="text-text mt-2">{mark.utterance}</p>
      {mark.answer.text && <p className="text-dim text-[13px] mt-1">{mark.answer.text}</p>}
      <MetaLine mark={mark} />
      <div className="flex items-center gap-2 mt-3">
        <Link to={`/tutor?spatial=${mark.id}`}><Button size="sm" variant="ghost">Continue in tutor</Button></Link>
        {quiz.isSuccess ? (
          <Button size="sm" variant="ghost" disabled>In your review queue{due ? ` (due ${due})` : ''}</Button>
        ) : (
          <Button size="sm" variant="ghost" onClick={() => quiz.mutate(mark.id)} disabled={quiz.isPending}>Quiz me later</Button>
        )}
      </div>
    </div>
  );
}

export function PointAskPage() {
  const version = useExtensionDetect();
  const { data, isPending, error } = useSpatial();

  return (
    <>
      <PageHeader
        eyebrow="Point & Ask"
        title="Circle it. Ask it."
        subtitle="Marks are references, never authority: StudyOS explains what you marked and never acts on the page."
      />
      <ExtensionCard version={version} />
      <Card eyebrow="Marks" title="Everything you circled">
        {isPending ? <Spinner /> : error ? (
          <EmptyState title="Marks unavailable" body={error.message} />
        ) : (data || []).length === 0 ? (
          <EmptyState title="No marks yet" body="Press Alt+Shift+A on any page with the extension installed." />
        ) : (
          <div className="grid gap-3">
            {(data || []).map(mark => <MarkRow key={mark.id} mark={mark} />)}
          </div>
        )}
      </Card>
    </>
  );
}
