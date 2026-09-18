import { FormEvent, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Phase, Topic } from '@/api/types';
import { Button, Card, EmptyState, Field, Input, Modal, PageHeader, Spinner, Tag, Textarea } from '@/components';
import { useDashboard } from '../today/useDashboard';
import { Assessment, AttemptResult, useTopicActions } from './useRoadmap';

interface Coverage { objectives: { title: string; covered: boolean }[] }

function QuizModal({ topic, actions, onClose }: { topic: Topic; actions: ReturnType<typeof useTopicActions>; onClose: () => void }) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [answers, setAnswers] = useState<string[]>([]);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState('');

  const start = async () => {
    setError('');
    try {
      const data = await actions.startAssessment.mutateAsync(topic.id);
      setAssessment(data);
      setAnswers(data.questions.map(() => ''));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const submit = async () => {
    if (!assessment) return;
    setError('');
    try {
      setResult(await actions.submitAttempt.mutateAsync({ id: assessment.id, answers }));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Modal open title={`Quiz · ${topic.title}`} onClose={onClose}>
      {!assessment && !result && (
        <div className="grid gap-3">
          <p className="text-dim text-[13px]">Start an assessment to check your mastery of this topic.</p>
          {error && <p className="text-red text-[13px]">{error}</p>}
          <div><Button size="sm" onClick={start} loading={actions.startAssessment.isPending}>Start quiz</Button></div>
        </div>
      )}
      {assessment && !result && (
        <div className="grid gap-4">
          {assessment.questions.map((q, i) => (
            <div key={i}>
              <p className="text-text mb-2">{q.prompt}</p>
              {q.options && q.options.length > 0 ? (
                <div className="grid gap-1">
                  {q.options.map(opt => (
                    <label key={opt} className="flex items-center gap-2 text-dim text-[14px]">
                      <input type="radio" name={`q-${i}`} checked={answers[i] === opt} onChange={() => setAnswers(a => a.map((v, j) => (j === i ? opt : v)))} />
                      {opt}
                    </label>
                  ))}
                </div>
              ) : (
                <Input value={answers[i]} onChange={e => setAnswers(a => a.map((v, j) => (j === i ? e.target.value : v)))} placeholder="Your answer" />
              )}
            </div>
          ))}
          {error && <p className="text-red text-[13px]">{error}</p>}
          <div><Button size="sm" onClick={submit} loading={actions.submitAttempt.isPending}>Submit answers</Button></div>
        </div>
      )}
      {result && (
        <div className="grid gap-3">
          <p className="text-text">Score: <span className="font-mono">{Math.round(result.score * 100)}%</span></p>
          <p className="text-dim text-[13px]">{result.feedback}</p>
          <div><Button size="sm" variant="ghost" onClick={onClose}>Close</Button></div>
        </div>
      )}
    </Modal>
  );
}

function AddTopicForm({ phase, actions }: { phase: Phase; actions: ReturnType<typeof useTopicActions> }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [minutes, setMinutes] = useState('');

  const submit = (e: FormEvent) => {
    e.preventDefault();
    actions.addTopic.mutate(
      { phase_id: phase.id, title, description: description || undefined, estimated_minutes: minutes ? Number(minutes) : undefined },
      { onSuccess: () => { setTitle(''); setDescription(''); setMinutes(''); setOpen(false); } },
    );
  };

  if (!open) return <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>+ Add topic</Button>;
  return (
    <form onSubmit={submit} className="grid gap-3 border border-line p-3">
      <Field label="Title"><Input value={title} onChange={e => setTitle(e.target.value)} required /></Field>
      <Field label="Description"><Textarea value={description} onChange={e => setDescription(e.target.value)} /></Field>
      <Field label="Estimated minutes"><Input type="number" min={0} value={minutes} onChange={e => setMinutes(e.target.value)} /></Field>
      <div className="flex gap-2">
        <Button size="sm" type="submit" loading={actions.addTopic.isPending}>Add topic</Button>
        <Button size="sm" variant="ghost" type="button" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </form>
  );
}

export function RoadmapPage() {
  const { data, isPending, error } = useDashboard();
  const goalId = data?.goal?.id ?? '';
  const actions = useTopicActions(goalId);
  const coverage = useQuery({
    queryKey: ['goals', goalId, 'coverage'],
    queryFn: () => api<Coverage>(`/api/goals/${goalId}/coverage`),
    enabled: Boolean(goalId),
  });
  const [quizTopic, setQuizTopic] = useState<Topic | null>(null);

  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error) return <EmptyState title="Roadmap is unavailable" body={error.message} />;
  if (!data || !data.goal) return <EmptyState title="No goal yet" body="Create a goal to see your roadmap." />;

  const { goal } = data;

  return (
    <>
      <PageHeader eyebrow="Roadmap" title={goal.title} actions={
        <div className="flex gap-2">
          <Tag tone="accent">{goal.goal_type}</Tag>
          <Tag>{goal.weekly_hours}h / week</Tag>
          {goal.target_date && <Tag>{goal.target_date}</Tag>}
        </div>
      } />
      {goal.phases.map(phase => (
        <Card key={phase.id} eyebrow={`Phase ${phase.order_index + 1}`} title={phase.title} className="mb-6">
          <div className="grid gap-3 mb-4">
            {phase.topics.map(topic => (
              <div key={topic.id} className="flex items-center justify-between gap-4 border border-line p-3">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    aria-label={`${topic.title} progress`}
                    checked={topic.progress >= 1}
                    onChange={e => actions.setProgress.mutate({ id: topic.id, progress: e.target.checked ? 1 : 0 })}
                  />
                  <div>
                    <p className="text-text">{topic.title}</p>
                    {topic.description && <p className="text-dim text-[13px] mt-0.5">{topic.description}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Tag tone="muted">{topic.difficulty}</Tag>
                  <span className="font-mono text-dim text-[12px]">{Math.round(topic.mastery * 100)}%</span>
                  <Button size="sm" variant="ghost" onClick={() => setQuizTopic(topic)}>Quiz</Button>
                </div>
              </div>
            ))}
          </div>
          <AddTopicForm phase={phase} actions={actions} />
        </Card>
      ))}
      <Card eyebrow="Coverage" title="Objectives">
        {coverage.isPending ? <Spinner /> : (coverage.data?.objectives || []).length === 0 ? (
          <p className="text-dim text-[13px]">No objectives tracked for this goal.</p>
        ) : (
          <div className="grid gap-2">
            {(coverage.data?.objectives || []).map((o, i) => (
              <div key={i} className="flex items-center justify-between gap-4 border border-line p-3">
                <p className="text-text">{o.title}</p>
                <Tag tone={o.covered ? 'accent' : 'yellow'}>{o.covered ? 'covered' : 'uncovered'}</Tag>
              </div>
            ))}
          </div>
        )}
      </Card>
      {quizTopic && <QuizModal topic={quizTopic} actions={actions} onClose={() => setQuizTopic(null)} />}
    </>
  );
}
