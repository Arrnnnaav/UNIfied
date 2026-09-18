import { Card, EmptyState, PageHeader, Spinner, Stat, Table } from '@/components';
import { useAnalytics, useCoverage } from './useOperator';

export function AnalyticsPage() {
  const analytics = useAnalytics();
  const coverage = useCoverage();

  if (analytics.isPending) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (analytics.error || !analytics.data) return <EmptyState title="Analytics unavailable" body={analytics.error?.message} />;
  const a = analytics.data;
  const runtime = Object.entries(a.model_health.runtime);
  const providerHint = Object.entries(a.spatial_cost.by_provider_usd).map(([p, v]) => `${p} $${v.toFixed(4)}`).join(' · ');

  return (
    <>
      <PageHeader eyebrow="Operator" title="Analytics" subtitle="Learning outcomes, model health and cost." />
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Stat label="Mastery: not started" value={a.mastery_buckets.not_started} />
        <Stat label="Mastery: developing" value={a.mastery_buckets.developing} />
        <Stat label="Mastery: mastered" value={a.mastery_buckets.mastered} />
        <Stat label="Spatial asks today" value={a.spatial_cost.asks_today} />
        <Stat label="Spatial spend today" value={`$${a.spatial_cost.today_usd.toFixed(4)}`} hint={providerHint || undefined} />
        <Stat label="Ingestion failure rate" value={`${Math.round(a.quality.ingestion_failure_rate * 100)}%`} />
      </div>
      {runtime.length > 0 && (
        <Card eyebrow="Model health" title="Latency & fallback by task" className="mb-6">
          <Table
            rows={runtime.map(([task, r]) => ({ task, ...r }))}
            rowKey={r => r.task}
            columns={[
              { key: 'task', header: 'Task' },
              { key: 'count', header: 'Calls' },
              { key: 'p50_latency_ms', header: 'p50', render: r => <span className="font-mono text-[12px]">{r.p50_latency_ms}ms</span> },
              { key: 'p95_latency_ms', header: 'p95', render: r => <span className="font-mono text-[12px]">{r.p95_latency_ms}ms</span> },
              { key: 'fallback_rate', header: 'Fallback', render: r => <span className="font-mono text-[12px]">{Math.round(r.fallback_rate * 100)}%</span> },
              { key: 'providers', header: 'Providers', render: r => r.providers.join(', ') },
            ]}
          />
        </Card>
      )}
      <Card eyebrow="Clients" title="Spatial client versions" className="mb-6">
        <Table
          rows={Object.entries(a.spatial_cost.client_versions).map(([version, count]) => ({ version, count }))}
          rowKey={r => r.version}
          columns={[
            { key: 'version', header: 'Version', render: r => <span className="font-mono text-[12px]">{r.version}</span> },
            { key: 'count', header: 'Events' },
          ]}
        />
      </Card>
      <Card eyebrow="Coverage" title={`Content gaps${coverage.data ? `: ${coverage.data.content_gaps} topics under-covered, avg ${Math.round(coverage.data.average_coverage * 100)}%` : ''}`}>
        {coverage.isPending ? <Spinner /> : coverage.error ? (
          <p className="text-red text-[13px]">{coverage.error.message}</p>
        ) : (
          <Table
            rows={(coverage.data?.topics || []).filter(t => t.covered_objectives < t.objectives)}
            empty="Every objective is covered."
            rowKey={t => t.topic_id}
            columns={[
              { key: 'title', header: 'Topic' },
              { key: 'objectives', header: 'Objectives' },
              { key: 'covered_objectives', header: 'Covered' },
              { key: 'coverage', header: 'Coverage', render: t => <span className="font-mono text-[12px]">{Math.round(t.coverage * 100)}%</span> },
            ]}
          />
        )}
      </Card>
    </>
  );
}
