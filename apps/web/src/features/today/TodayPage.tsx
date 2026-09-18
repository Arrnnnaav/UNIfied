import { Link } from 'react-router-dom';
import { Button, Card, EmptyState, PageHeader, Spinner, Stat, Tag } from '@/components';
import type { TodayItem } from '@/api/types';
import { useDashboard, useReviewQueue, useSessionActions } from './useDashboard';

export function TodayPage() {
  const { data, isPending, error } = useDashboard();
  const review = useReviewQueue();
  const { start, update, completeReview } = useSessionActions();

  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error) return <EmptyState title="Today is unavailable" body={error.message} />;
  if (!data || !data.goal) return <EmptyState title="Pick your first goal" body="Your roadmap, reviews and recommendations follow the goal." action={<Link to="/onboarding"><Button>New goal</Button></Link>} />;

  const { goal, today, spatial_reviews, sessions, stats } = data;
  const pct = Math.round((stats.average_mastery || 0) * 100);

  return (
    <>
      <PageHeader eyebrow="Today" title="Make progress that counts." subtitle="Completion is activity. Mastery is evidence." />
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Stat label="Topics" value={stats.topics} />
        <Stat label="Mastered" value={stats.mastered} />
        <Stat label="Avg mastery" value={`${pct}%`} />
      </div>
      <Card eyebrow="Next best actions" title={goal.title} className="mb-6">
        {today.length === 0 ? <EmptyState title="All caught up" body="No pending actions for this goal." /> : (
          <div className="grid gap-3">
            {today.map((item: TodayItem, i: number) => (
              <div key={`${item.topic_id || 'row'}-${i}`} className="flex items-center justify-between gap-4 border border-line p-3">
                <div>
                  <p className="text-text">{item.action}</p>
                  <p className="text-dim text-[13px] mt-0.5">{item.reason}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-dim text-[12px]">{item.estimated_minutes}m</span>
                  <Tag tone={item.priority === 'high' ? 'accent2' : 'muted'}>{item.kind}</Tag>
                  <Button size="sm" variant="ghost" onClick={() => start.mutate({ goal_id: goal.id, topic_id: item.topic_id || null, kind: item.kind, planned_minutes: item.estimated_minutes })} disabled={start.isPending}>Start session</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
      {spatial_reviews.length > 0 && (
        <Card eyebrow="Point & Ask review" title="Things you circled that are due" className="mb-6">
          <div className="grid gap-3">
            {spatial_reviews.map(item => (
              <div key={item.id} className="flex items-center justify-between gap-4 border border-line p-3">
                <div>
                  <p className="text-text">{item.title}</p>
                  <p className="text-dim text-[13px] mt-0.5">{item.reason}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-dim text-[12px]">{item.minutes}m</span>
                  <Link to={`/tutor?spatial=${item.spatial_context_id}`}><Button size="sm" variant="ghost">Open in tutor</Button></Link>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
      {(sessions.length > 0) && (
        <Card eyebrow="Sessions" title="Continue where you left off" className="mb-6">
          <div className="grid gap-3">
            {sessions.map(s => (
              <div key={s.id} className="flex items-center justify-between gap-4 border border-line p-3">
                <div>
                  <p className="text-text">{s.kind} · {s.topic || 'Goal session'}</p>
                  <p className="text-dim text-[13px] mt-0.5">{s.planned_minutes} min planned</p>
                </div>
                <div className="flex items-center gap-2">
                  <Tag tone={s.status === 'active' ? 'accent2' : 'muted'}>{s.status}</Tag>
                  {s.status === 'planned' && <Button size="sm" variant="ghost" onClick={() => update.mutate({ id: s.id, status: 'active' })}>Start</Button>}
                  {s.status === 'active' && <Button size="sm" variant="ghost" onClick={() => update.mutate({ id: s.id, status: 'completed', actual_minutes: s.planned_minutes })}>Complete</Button>}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
      <Card eyebrow="Review queue" title="Spaced repetition">
        {review.isPending ? <Spinner /> : (review.data || []).length === 0 ? (
          <p className="text-dim text-[13px]">Nothing due. Reviews appear as you learn and mark things for later.</p>
        ) : (
          <div className="grid gap-3">
            {(review.data || []).map(item => (
              <div key={item.id} className="flex items-center justify-between gap-4 border border-line p-3">
                <div>
                  <p className="text-text">{item.prompt || item.topic}</p>
                  <p className="text-dim text-[13px] mt-0.5">due {new Date(item.due_at).toLocaleDateString()}</p>
                </div>
                <Button size="sm" variant="ghost" onClick={() => completeReview.mutate(item.id)} disabled={completeReview.isPending}>Done</Button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}
