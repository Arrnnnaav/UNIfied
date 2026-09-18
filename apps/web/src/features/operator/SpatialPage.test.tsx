import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { SpatialPage } from './SpatialPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: 'op1', name: 'Op', email: 'op@x', role: 'operator', student_id: null, has_goals: true, profile_complete: true };

const snapshot = {
  users: [], goals: [], resources: [], ingestion_jobs: [], audit_log: [], packages: [], monitoring_dashboards: [],
  spatial_review: [{ id: 's1', goal_id: null, confidence: 0.42, review_status: 'pending', page_title: 'Graphing parabolas', processing_ms: 812, utterance_preview: 'what does this vertex mean?' }],
  privacy: { raw_resource_text: false, raw_screen_pixels: false, operator_access: 'metadata_and_quality_signals' },
};

const analytics = {
  mastery_buckets: { not_started: 0, developing: 0, mastered: 0 },
  resource_trust: {}, ingestion_status: {},
  spatial_cost: { today_usd: 0.0123, by_provider_usd: { openai: 0.0123 }, asks_today: 7, review: { pending: 1 }, client_versions: {} },
  spatial: { count: 1, low_confidence: 1, avg_confidence: 0.42, avg_latency_ms: 800, p50_latency_ms: 800, p95_latency_ms: 900, max_latency_ms: 900 },
  quality: { ingestion_failure_rate: 0, trusted_resources: 0, spatial_corrections: 0, spatial_correction_rate: 0 },
  assessment: { attempts: 0, average_score: 0 },
  review: { due: 0, scheduled: 0 },
  sessions: { total: 0, planned: 0, active: 0, completed: 0, minutes: 0 },
  model_health: { embedding_backend: 'ollama', local_embedding_enabled: true, tutor_route: {}, spatial_route: {}, vision_route: { provider: 'local', model: 'x', optional: true }, cloud_fallback_configured: false, runtime: {} },
  privacy: 'aggregates only',
};

test('confirming a spatial review item PATCHes the review endpoint', async () => {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/operator/snapshot': { body: snapshot },
    'GET /api/operator/analytics': { body: analytics },
    'PATCH /api/operator/spatial/s1/review': (init) => ({ body: { id: 's1', review_status: 'confirmed', confidence: 0.99, sent: JSON.parse(String(init?.body)) } }),
  });
  renderWithProviders(<AuthProvider><ToastProvider><SpatialPage /></ToastProvider></AuthProvider>);
  expect(await screen.findByText('Graphing parabolas')).toBeInTheDocument();
  expect(screen.getByText('42%')).toBeInTheDocument();
  expect(screen.getByText('$0.0123')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }));
  await waitFor(() => {
    const call = calls.find(c => c.method === 'PATCH' && c.path === '/api/operator/spatial/s1/review');
    expect(call).toBeTruthy();
    expect(JSON.parse(String(call?.init?.body))).toEqual({ action: 'confirm' });
  });
});
