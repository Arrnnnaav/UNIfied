import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { RoadmapPage } from './RoadmapPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true };

const dashboard = {
  user: { name: 'A' },
  goal: {
    id: 'g1', title: 'Learn Linear Algebra', goal_type: 'skill', target_date: '2026-12-01', weekly_hours: 8, status: 'active',
    phases: [
      {
        id: 'p1', title: 'Foundations', order_index: 0,
        topics: [
          { id: 't1', title: 'Vectors', description: '', difficulty: 'easy', estimated_minutes: 30, progress: 0, mastery: 0.4, phase_id: 'p1', resource_count: 0 },
          { id: 't2', title: 'Matrices', description: '', difficulty: 'medium', estimated_minutes: 45, progress: 0, mastery: 0.1, phase_id: 'p1', resource_count: 0 },
        ],
      },
    ],
  },
  today: [], spatial_reviews: [], sessions: [], plan_status: {}, stats: { topics: 2, mastered: 0, average_mastery: 0.25 },
};

test('renders phases and topics; toggling checkbox PATCHes progress', async () => {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/dashboard': { body: dashboard },
    'GET /api/goals/g1/coverage': { body: { objectives: [{ title: 'Solve systems', covered: false }] } },
    'PATCH /api/topics/t1/progress': (init) => ({ body: JSON.parse(String(init?.body)) }),
  });
  renderWithProviders(<AuthProvider><ToastProvider><RoadmapPage /></ToastProvider></AuthProvider>);

  expect(await screen.findByText('Foundations')).toBeInTheDocument();
  expect(screen.getByText('Vectors')).toBeInTheDocument();
  expect(screen.getByText('Matrices')).toBeInTheDocument();

  await userEvent.click(screen.getByLabelText('Vectors progress'));
  await waitFor(() => {
    const patch = calls.find(c => c.method === 'PATCH' && c.path === '/api/topics/t1/progress');
    expect(patch).toBeTruthy();
    expect(JSON.parse(String(patch?.init?.body))).toEqual({ progress: 1 });
  });
});
