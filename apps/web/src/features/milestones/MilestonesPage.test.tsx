import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { MilestonesPage } from './MilestonesPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true };
const dashboard = {
  user: { name: 'A' },
  goal: { id: 'g1', title: 'Learn Linear Algebra', goal_type: 'skill', target_date: null, weekly_hours: 8, status: 'active', phases: [] },
  today: [], spatial_reviews: [], sessions: [], plan_status: {}, stats: { topics: 0, mastered: 0, average_mastery: 0 },
};
const milestone = {
  id: 'm1', goal_id: 'g1', title: 'Finish foundations', description: 'Complete phase 1', badge_title: '',
  target_date: null, criteria: {}, progress: 1, status: 'completed', completed_at: '2026-09-10T00:00:00',
};

function setup(routes: Parameters<typeof mockFetch>[0] = {}) {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/dashboard': { body: dashboard },
    'GET /api/milestones': { body: [milestone] },
    'GET /api/milestone-shares': { body: [] },
    ...routes,
  });
  renderWithProviders(<AuthProvider><ToastProvider><MilestonesPage /></ToastProvider></AuthProvider>);
  return { calls };
}

test('renders a milestone', async () => {
  setup();
  expect(await screen.findByText('Finish foundations')).toBeInTheDocument();
  expect(screen.getByText('Complete phase 1')).toBeInTheDocument();
  expect(screen.getByText(/^achieved /)).toBeInTheDocument();
});

test('creating a milestone POSTs /api/milestones', async () => {
  const { calls } = setup({ 'POST /api/milestones': init => ({ body: JSON.parse(String(init?.body)) }) });
  expect(await screen.findByText('Finish foundations')).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText('Milestone title'), 'Pass midterm');
  await userEvent.type(screen.getByLabelText('Milestone description'), 'Ace it');
  await userEvent.click(screen.getByRole('button', { name: /create milestone/i }));
  await waitFor(() => {
    const post = calls.find(c => c.method === 'POST' && c.path === '/api/milestones');
    expect(post).toBeTruthy();
    expect(JSON.parse(String(post?.init?.body))).toEqual({ goal_id: 'g1', title: 'Pass midterm', description: 'Ace it' });
  });
});
