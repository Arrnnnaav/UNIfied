import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { OnboardingPage } from './OnboardingPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

test('skip profile, create goal, land on today', async () => {
  setToken('t');
  let goals = false;
  const { calls } = mockFetch({
    'GET /api/auth/me': () => ({ body: { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: goals, profile_complete: false } }),
    'POST /api/goals': (init) => { goals = true; return { body: { id: 'g1', ...JSON.parse(String(init?.body)), phases: [] } }; },
  });
  renderWithProviders(<AuthProvider><Routes><Route path="/onboarding" element={<OnboardingPage />} /><Route path="/" element={<p>today page</p>} /></Routes></AuthProvider>, { route: '/onboarding' });
  await userEvent.click(await screen.findByRole('button', { name: /skip/i }));
  await userEvent.type(screen.getByLabelText(/goal title/i), 'Learn linear algebra');
  await userEvent.click(screen.getByRole('button', { name: /create my plan/i }));
  expect(await screen.findByText('today page')).toBeInTheDocument();
  expect(calls.some(c => c.method === 'POST' && c.path === '/api/goals')).toBe(true);
});
