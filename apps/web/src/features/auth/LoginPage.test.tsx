import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/auth/AuthProvider';
import { LoginPage } from './LoginPage';
import { RequireStudent } from '@/auth/guards';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

test('signs in, stores token, navigates to next', async () => {
  mockFetch({
    'POST /api/auth/login': { body: { access_token: 'tok', token_type: 'bearer', user: { id: '1', student_id: 'S1', name: 'A', role: 'student' } } },
    'GET /api/auth/me': { body: { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true } },
  });
  renderWithProviders(<AuthProvider><Routes><Route path="/login" element={<LoginPage />} /><Route path="/" element={<p>today page</p>} /></Routes></AuthProvider>, { route: '/login' });
  await userEvent.type(screen.getByLabelText(/email/i), 'a@x');
  await userEvent.type(screen.getByLabelText(/password/i), 'secret-pass');
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
  expect(await screen.findByText('today page')).toBeInTheDocument();
  expect(localStorage.getItem('studyos_token')).toBe('tok');
});

test('login without a stored token passes the guard instead of bouncing to /login (regression: provider cached token=null)', async () => {
  // No setToken(): the provider starts believing there is no session, exactly like a cold load.
  mockFetch({
    'POST /api/auth/login': { body: { access_token: 'tok', token_type: 'bearer', user: { id: '1', student_id: 'S1', name: 'A', role: 'student' } } },
    'GET /api/auth/me': { body: { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true } },
  });
  renderWithProviders(
    <AuthProvider><Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireStudent />}><Route path="/" element={<p>today page</p>} /></Route>
    </Routes></AuthProvider>,
    { route: '/login' },
  );
  await userEvent.type(screen.getByLabelText(/email/i), 'a@x');
  await userEvent.type(screen.getByLabelText(/password/i), 'secret-pass');
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
  expect(await screen.findByText('today page')).toBeInTheDocument();
  expect(screen.queryByText(/sign in to your learning space/i)).not.toBeInTheDocument();
});

test('shows API error inline', async () => {
  mockFetch({ 'POST /api/auth/login': { status: 401, body: { detail: 'invalid credentials' } } });
  renderWithProviders(<AuthProvider><Routes><Route path="/login" element={<LoginPage />} /></Routes></AuthProvider>, { route: '/login' });
  await userEvent.type(screen.getByLabelText(/email/i), 'a@x');
  await userEvent.type(screen.getByLabelText(/password/i), 'wrong-pass');
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
  expect(await screen.findByText('invalid credentials')).toBeInTheDocument();
});
