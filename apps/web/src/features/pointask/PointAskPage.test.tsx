import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { PointAskPage } from './PointAskPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true };

const mark = {
  id: 'c1', goal_id: 'g1', utterance: 'why is the sign negative?', marks: [], source: 'extension', confidence: 0.9, review_status: 'pending',
  page: { url: 'https://example.com/notes', title: 'Linear algebra notes', surface: 'web' },
  answer: { text: 'Because the direction is reversed.', anchors_used: [{ text: 'a' }], meta: { provider: 'openai', model: 'gpt-5' } },
  turns: 1, created_at: '2026-09-18T00:00:00',
};

afterEach(() => { delete document.documentElement.dataset.pointAskExtension; });

function renderPage() {
  return renderWithProviders(<AuthProvider><ToastProvider><PointAskPage /></ToastProvider></AuthProvider>);
}

test('shows detected extension version', async () => {
  setToken('t');
  document.documentElement.dataset.pointAskExtension = '0.2.0';
  mockFetch({ 'GET /api/auth/me': { body: me }, 'GET /api/spatial-context': { body: [] } });
  renderPage();
  expect(await screen.findByText(/Extension installed \(v0\.2\.0\)/)).toBeInTheDocument();
});

test('shows install steps when extension is absent', async () => {
  setToken('t');
  mockFetch({ 'GET /api/auth/me': { body: me }, 'GET /api/spatial-context': { body: [] } });
  renderPage();
  expect(await screen.findByText(/Install StudyOS Point & Ask/)).toBeInTheDocument();
  expect(screen.getByText(/Alt\+Shift\+A/)).toBeInTheDocument();
});

test('renders a mark and quizzes it later', async () => {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/spatial-context': { body: [mark] },
    'POST /api/spatial-context/c1/quiz': { body: { due_at: '2026-09-20T00:00:00' } },
  });
  renderPage();
  expect(await screen.findByText('Linear algebra notes')).toBeInTheDocument();
  expect(screen.getByText('why is the sign negative?')).toBeInTheDocument();
  expect(screen.getByText('Because the direction is reversed.')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /quiz me later/i }));
  await waitFor(() => expect(calls.some(c => c.method === 'POST' && c.path === '/api/spatial-context/c1/quiz')).toBe(true));
  expect(await screen.findByRole('button', { name: /In your review queue/ })).toBeDisabled();
});
