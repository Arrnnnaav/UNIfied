import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { MonitoringPage } from './MonitoringPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true };

test('join form POSTs /api/monitoring/join/ABC123', async () => {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/monitoring-dashboards': { body: [] },
    'POST /api/monitoring/join/ABC123': { body: { dashboard_id: 'd1', status: 'joined' } },
  });
  renderWithProviders(<AuthProvider><ToastProvider><MonitoringPage /></ToastProvider></AuthProvider>);
  await userEvent.type(await screen.findByLabelText('Access code'), 'ABC123');
  await userEvent.click(screen.getByRole('button', { name: /^join$/i }));
  await waitFor(() => expect(calls.some(c => c.method === 'POST' && c.path === '/api/monitoring/join/ABC123')).toBe(true));
});
