import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { ResourcesPage } from './ResourcesPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: 'op1', name: 'Op', email: 'op@x', role: 'operator', student_id: null, has_goals: true, profile_complete: true };

const snapshot = {
  users: [], goals: [], spatial_review: [], audit_log: [], packages: [], monitoring_dashboards: [],
  resources: [{ id: 'r1', title: 'Vectors notes', source_type: 'pdf', status: 'ready', trust_status: 'unverified', has_content: true, document_count: 1 }],
  ingestion_jobs: [{ id: 'j1', resource_id: 'r1', kind: 'pdf_parse', status: 'failed', progress: 40, error: 'boom' }],
  privacy: { raw_resource_text: false, raw_screen_pixels: false, operator_access: 'metadata_and_quality_signals' },
};

test('verify PATCHes trust and retry POSTs the retry endpoint', async () => {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/operator/snapshot': { body: snapshot },
    'PATCH /api/operator/resources/r1/trust': { body: { id: 'r1', trust_status: 'verified' } },
    'POST /api/operator/ingestion/j1/retry': { body: { id: 'j1', status: 'queued', enqueued: true } },
  });
  renderWithProviders(<AuthProvider><ToastProvider><ResourcesPage /></ToastProvider></AuthProvider>);
  expect(await screen.findByText('Vectors notes')).toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: /verify/i }));
  await waitFor(() => {
    const url = calls.find(c => c.method === 'PATCH' && c.path === '/api/operator/resources/r1/trust');
    expect(url).toBeTruthy();
    expect(String(url?.init?.headers && (url.init.headers as Record<string, string>)['Content-Type'] || '')).not.toContain('application/json');
  });

  await userEvent.click(screen.getByRole('button', { name: /retry/i }));
  await waitFor(() => {
    expect(calls.some(c => c.method === 'POST' && c.path === '/api/operator/ingestion/j1/retry')).toBe(true);
  });
});
