import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { ResourcesPage } from './ResourcesPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true };

const dashboard = {
  user: { name: 'A' },
  goal: {
    id: 'g1', title: 'Learn LA', goal_type: 'skill', target_date: null, weekly_hours: 8, status: 'active', phases: [],
    resources: [{ id: 'r1', title: 'Khan notes', source_type: 'url', status: 'indexed', trust_status: 'verified' }],
  },
  today: [], spatial_reviews: [], sessions: [], plan_status: {}, stats: { topics: 0, mastered: 0, average_mastery: 0 },
};

test('renders library; URL form creates resource then ingests', async () => {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/dashboard': { body: dashboard },
    'GET /api/ingestion/jobs': { body: [] },
    'POST /api/resources': { body: { id: 'r2', title: 'Article', source_type: 'url', status: 'pending', trust_status: 'unverified' } },
    'POST /api/resources/r2/ingest-url': { body: { id: 'j1' } },
  });
  renderWithProviders(<AuthProvider><ToastProvider><ResourcesPage /></ToastProvider></AuthProvider>);

  expect(await screen.findByText('Khan notes')).toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: 'URL' }));
  await userEvent.type(screen.getByLabelText('Title'), 'Article');
  await userEvent.type(screen.getByLabelText('URL'), 'https://example.com/a');
  await userEvent.click(screen.getByRole('button', { name: 'Add' }));

  await waitFor(() => {
    expect(calls.some(c => c.method === 'POST' && c.path === '/api/resources')).toBe(true);
    expect(calls.some(c => c.method === 'POST' && c.path === '/api/resources/r2/ingest-url')).toBe(true);
  });
});
