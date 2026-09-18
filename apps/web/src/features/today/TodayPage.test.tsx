import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { TodayPage } from './TodayPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true };

test('shows stats, next actions and starts a session', async () => {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/review': { body: [] },
    'GET /api/dashboard': { body: { user: { name: 'A' }, goal: { id: 'g1', title: 'LA', goal_type: 'skill', target_date: null, weekly_hours: 8, status: 'active', phases: [] }, today: [{ topic_id: 't1', action: 'Review: Vectors', kind: 'review', estimated_minutes: 8, priority: 'high', reason: 'due', mastery: .4, dependencies: [] }], spatial_reviews: [{ id: 'r1', spatial_context_id: 'c1', title: 'Point & Ask: minus sign', minutes: 8, reason: 'you circled', due_at: '2026-09-19T00:00:00', kind: 'spatial_review' }], sessions: [], plan_status: {}, stats: { topics: 4, mastered: 1, average_mastery: .5 } } },
    'POST /api/learning-sessions': (init) => ({ body: { id: 's1', ...JSON.parse(String(init?.body)), status: 'planned', actual_minutes: 0, notes: '', started_at: null, completed_at: null, created_at: 'now', topic: 'Vectors' } }),
  });
  renderWithProviders(<AuthProvider><ToastProvider><TodayPage /></ToastProvider></AuthProvider>);
  expect(await screen.findByText('Review: Vectors')).toBeInTheDocument();
  expect(screen.getByText('4')).toBeInTheDocument();
  expect(screen.getByText('Point & Ask: minus sign')).toBeInTheDocument();
  await userEvent.click(screen.getAllByRole('button', { name: /start session/i })[0]);
  await waitFor(() => expect(calls.some(c => c.path === '/api/learning-sessions' && c.method === 'POST')).toBe(true));
});
