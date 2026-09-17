import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from './AuthProvider';
import { RequireOperator, RequireStudent } from './guards';
import { setToken } from './storage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = (over: Partial<{ role: string; has_goals: boolean }>) => ({ id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true, ...over });

function tree() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<p>login page</p>} />
        <Route path="/onboarding" element={<p>onboarding page</p>} />
        <Route element={<RequireStudent />}><Route path="/" element={<p>today page</p>} /></Route>
        <Route path="/operator/login" element={<p>operator login</p>} />
        <Route element={<RequireOperator />}><Route path="/operator" element={<p>operator home</p>} /></Route>
      </Routes>
    </AuthProvider>
  );
}

test('no token -> /login', async () => {
  mockFetch({});
  renderWithProviders(tree(), { route: '/' });
  expect(await screen.findByText('login page')).toBeInTheDocument();
});

test('student without goals -> /onboarding', async () => {
  setToken('t'); mockFetch({ 'GET /api/auth/me': { body: me({ has_goals: false }) } });
  renderWithProviders(tree(), { route: '/' });
  expect(await screen.findByText('onboarding page')).toBeInTheDocument();
});

test('student with goals sees today', async () => {
  setToken('t'); mockFetch({ 'GET /api/auth/me': { body: me({}) } });
  renderWithProviders(tree(), { route: '/' });
  expect(await screen.findByText('today page')).toBeInTheDocument();
});

test('student on operator route sees not-an-operator', async () => {
  setToken('t'); mockFetch({ 'GET /api/auth/me': { body: me({}) } });
  renderWithProviders(tree(), { route: '/operator' });
  expect(await screen.findByText(/not an operator/i)).toBeInTheDocument();
});

test('operator reaches operator home', async () => {
  setToken('t'); mockFetch({ 'GET /api/auth/me': { body: me({ role: 'operator' }) } });
  renderWithProviders(tree(), { route: '/operator' });
  expect(await screen.findByText('operator home')).toBeInTheDocument();
});
