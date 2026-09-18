import { FormEvent, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { SpatialContext } from '@/api/types';
import { Button, Card, Field, Select, Tag, Textarea, PageHeader, useToast } from '@/components';
import { useDashboard } from '@/features/today/useDashboard';
import { useTutorStream, TutorAnswer } from './useTutorStream';

interface Message { id: number; question: string; answer: TutorAnswer | null; pending: boolean }

const truncate = (s: string, n = 60) => (s.length > n ? `${s.slice(0, n)}…` : s);

function AnswerView({ message }: { message: Message }) {
  const [open, setOpen] = useState<Record<number, boolean>>({});
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] border border-line bg-surface p-3">
        {message.pending && !message.answer ? (
          <p className="text-dim text-[13px]">Retrieving evidence…</p>
        ) : (
          <>
            <p className="text-text whitespace-pre-wrap">{message.answer?.answer}</p>
            {(message.answer?.citations?.length ?? 0) > 0 && (
              <div className="flex flex-wrap items-center gap-2 mt-3">
                {message.answer!.citations.map((c, i) => (
                  <span key={i}>
                    <button type="button" onClick={() => setOpen(o => ({ ...o, [i]: !o[i] }))} aria-expanded={Boolean(open[i])}>
                      <Tag tone="accent">{c.title}</Tag>
                    </button>
                    {open[i] && <p className="text-dim text-[12px] mt-1 border-l border-strong pl-2">{c.snippet}</p>}
                  </span>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export function TutorPage() {
  const [params] = useSearchParams();
  const spatialParam = params.get('spatial') || '';
  const { data: dashboard } = useDashboard();
  const spatial = useQuery({ queryKey: ['spatial'], queryFn: () => api<SpatialContext[]>('/api/spatial-context') });
  const { ask, status, answer, streamed, error, cancel } = useTutorStream();
  const { push } = useToast();

  const [question, setQuestion] = useState('');
  const [spatialId, setSpatialId] = useState(spatialParam);
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => { setSpatialId(spatialParam); }, [spatialParam]);
  useEffect(() => { if (error) push(error, 'error'); }, [error, push]);

  useEffect(() => {
    if (status !== 'done' || !answer) return;
    setMessages(list => {
      const next = [...list];
      const last = next[next.length - 1];
      if (last?.pending) next[next.length - 1] = { ...last, answer, pending: false };
      return next;
    });
  }, [status, answer]);

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const q = question.trim();
    if (!q || status === 'retrieving') return;
    setMessages(list => [...list, { id: Date.now(), question: q, answer: null, pending: true }]);
    setQuestion('');
    const body: { question: string; goal_id?: string; spatial_context_id?: string } = { question: q };
    if (dashboard?.goal?.id) body.goal_id = dashboard.goal.id;
    if (spatialId) body.spatial_context_id = spatialId;
    void ask(body);
  };

  const marks = (spatial.data || []).slice(0, 20);

  return (
    <>
      <PageHeader eyebrow="Tutor" title="Ask anything." subtitle="Answers grounded in your saved material and marks." />

      <div className="grid gap-3 mb-6">
        {messages.length === 0 && (
          <Card eyebrow="Grounded answers" title="Start a conversation">
            <p className="text-dim text-[13px]">Ask about anything in your goal. Citations link back to your saved material.</p>
          </Card>
        )}
        {messages.map(m => (
          <div key={m.id} className="grid gap-2">
            <div className="flex justify-end">
              <div className="max-w-[80%] bg-accent-tint text-text p-3 border border-line">{m.question}</div>
            </div>
            <AnswerView message={m.pending && status === 'retrieving' && streamed ? { ...m, answer: { answer: streamed, citations: [] } } : m} />
          </div>
        ))}
      </div>

      {status === 'retrieving' && <p className="text-accent font-mono text-[13px] mb-3">Retrieving evidence…</p>}
      {error && <p className="text-red text-[13px] mb-3">{error}</p>}

      <form onSubmit={submit} className="grid gap-3">
        <Field label="Use a Point & Ask mark" hint="Optional — grounds the answer in a specific page you marked.">
          <Select value={spatialId} onChange={e => setSpatialId(e.target.value)}>
            <option value="">No mark selected</option>
            {marks.map(m => (
              <option key={m.id} value={m.id}>{truncate(`${m.page.title} · ${m.utterance}`)}</option>
            ))}
          </Select>
        </Field>
        <Textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="Ask a question… (Enter to send, Shift+Enter for a new line)"
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
          }}
        />
        <div className="flex gap-2">
          {status === 'retrieving' ? (
            <Button type="button" variant="danger" onClick={cancel}>Stop</Button>
          ) : (
            <Button type="submit" disabled={!question.trim()}>Ask</Button>
          )}
        </div>
      </form>
    </>
  );
}
