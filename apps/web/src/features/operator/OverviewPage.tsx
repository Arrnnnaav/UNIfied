import { Card, EmptyState, PageHeader, Spinner, Stat } from '@/components';
import { useOverview } from './useOperator';

export function OverviewPage() {
  const { data, isPending, error } = useOverview();
  if (isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error || !data) return <EmptyState title="Overview unavailable" body={error?.message} />;

  return (
    <>
      <PageHeader eyebrow="Operator" title="Platform overview" subtitle="Aggregate metadata only — private text and pixels never appear here." />
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Stat label="Users" value={data.users} />
        <Stat label="Goals" value={data.goals} />
        <Stat label="Resources" value={data.resources} />
        <Stat label="Ingestion ready" value={data.ingestion_ready} />
        <Stat label="Spatial contexts" value={data.spatial_contexts} hint={`${data.spatial_low_confidence} low confidence`} />
        <Stat label="Avg confidence" value={`${Math.round(data.spatial_avg_confidence * 100)}%`} hint={`~${data.spatial_avg_latency_ms}ms latency`} />
        <Stat label="Packages" value={data.packages} hint={`${data.published_packages} published`} />
        <Stat label="Dashboards" value={data.monitoring_dashboards} />
      </div>
      <Card eyebrow="Readiness" title="Content & pipeline readiness">
        <ul className="grid gap-2 text-[14px]">
          <li className="flex justify-between border-b border-line py-1.5"><span className="text-dim">Topics</span><span className="font-mono">{data.topics}</span></li>
          <li className="flex justify-between border-b border-line py-1.5"><span className="text-dim">Documents / chunks</span><span className="font-mono">{data.documents} / {data.chunks}</span></li>
          <li className="flex justify-between border-b border-line py-1.5"><span className="text-dim">Ingestion jobs</span><span className="font-mono">{data.ingestion_jobs}</span></li>
          <li className="flex justify-between border-b border-line py-1.5"><span className="text-dim">Sessions (completed)</span><span className="font-mono">{data.learning_sessions} ({data.completed_sessions})</span></li>
          <li className="flex justify-between py-1.5"><span className="text-dim">Model routes</span><span className="font-mono text-[12px]">{Object.entries(data.model_routes).map(([task, r]) => `${task}:${r.model || 'n/a'}`).join(' · ')}</span></li>
        </ul>
        <p className="text-muted text-[12px] mt-4">{data.privacy}</p>
      </Card>
    </>
  );
}
