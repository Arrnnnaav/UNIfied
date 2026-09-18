import { Button, Card, EmptyState, PageHeader, Spinner, Stat } from '@/components';
import { useAnalytics, useOperatorActions, useSnapshot } from './useOperator';

export function SpatialPage() {
  const snapshot = useSnapshot();
  const analytics = useAnalytics();
  const { reviewSpatial } = useOperatorActions();

  if (snapshot.isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (snapshot.error || !snapshot.data) return <EmptyState title="Spatial review unavailable" body={snapshot.error?.message} />;

  const items = snapshot.data.spatial_review;
  const cost = analytics.data?.spatial_cost;

  return (
    <>
      <PageHeader eyebrow="Operator" title="Spatial review" subtitle="Low-confidence Point & Ask resolutions awaiting a human decision." />
      {cost && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <Stat label="Asks today" value={cost.asks_today} />
          <Stat label="Spend today" value={`$${cost.today_usd.toFixed(4)}`} />
          <Stat label="By provider" value={Object.keys(cost.by_provider_usd).length} hint={Object.entries(cost.by_provider_usd).map(([p, v]) => `${p} $${v.toFixed(4)}`).join(' · ')} />
        </div>
      )}
      <Card eyebrow="Pending" title={`${items.length} to review`}>
        {items.length === 0 ? (
          <EmptyState title="All caught up" body="No low-confidence spatial resolutions right now." />
        ) : (
          <div className="grid gap-3">
            {items.map(item => (
              <div key={item.id} className="flex items-center justify-between gap-4 border border-line p-3">
                <div className="min-w-0">
                  <p className="text-text truncate">{item.page_title || 'Untitled page'}</p>
                  <p className="text-dim text-[13px] mt-0.5 truncate">“{item.utterance_preview}”</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="font-mono text-dim text-[12px]" title="confidence">{Math.round(item.confidence * 100)}%</span>
                  <span className="font-mono text-dim text-[12px]" title="latency">{item.processing_ms}ms</span>
                  <Button size="sm" variant="ghost" onClick={() => reviewSpatial.mutate({ id: item.id, action: 'confirm' })} disabled={reviewSpatial.isPending}>Confirm</Button>
                  <Button size="sm" variant="danger" onClick={() => reviewSpatial.mutate({ id: item.id, action: 'dismiss' })} disabled={reviewSpatial.isPending}>Dismiss</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}
