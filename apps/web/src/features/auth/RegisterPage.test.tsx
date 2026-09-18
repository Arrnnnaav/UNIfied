import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/auth/AuthProvider';
import { RegisterPage } from './RegisterPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

test('registers, stores token, navigates to onboarding', async () => {
  const { calls } = mockFetch({
    'POST /api/auth/register': { body: { access_token: 'tok', token_type: 'bearer', user: { id: '1', student_id: null, name: 'A', role: 'student' } } },
    'GET /api/auth/me': { body: { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: null, has_goals: false, profile_complete: false } },
  });
  renderWithProviders(<AuthProvider><Routes><Route path="/register" element={<RegisterPage />} /><Route path="/onboarding" element={<p>onboarding page</p>} /></Routes></AuthProvider>, { route: '/register' });
  await userEvent.type(screen.getByLabelText(/name/i), 'Ada');
  await userEvent.type(screen.getByLabelText(/email/i), 'a@x');
  await userEvent.type(screen.getByLabelText(/password/i), 'secret-pass');
  await userEvent.click(screen.getByRole('button', { name: /create account/i }));
  expect(await screen.findByText('onboarding page')).toBeInTheDocument();
  expect(localStorage.getItem('studyos_token')).toBe('tok');
  const registerCall = calls.find(c => c.path === '/api/auth/register');
  expect(JSON.parse(registerCall!.init!.body as string)).toEqual({ name: 'Ada', email: 'a@x', password: 'secret-pass' });
});
