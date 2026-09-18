import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { ToastProvider } from '@/components';
import { ProfilePage } from './ProfilePage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

const me = { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: true, profile_complete: true };
const profile = {
  id: 'p1', education_stage: 'undergraduate', graduation_year: 2027, current_skill_level: 'intermediate',
  known_skills: ['python', 'sql'], learning_modes: ['video'], preferred_pace: 'steady',
  constraints: 'Evenings only', college_name: 'IIT Example', college_year: '3', branch: 'CSE', college_id: 'C42',
  coding_profiles: {}, student_id: 'S1', name: 'A', email: 'a@x',
};

function setup(routes: Parameters<typeof mockFetch>[0] = {}) {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/me/profile': { body: profile },
    ...routes,
  });
  renderWithProviders(<AuthProvider><ToastProvider><ProfilePage /></ToastProvider></AuthProvider>);
  return { calls };
}

test('loads profile into inputs', async () => {
  setup();
  await waitFor(() => expect(screen.getByLabelText('Constraints')).toHaveValue('Evenings only'));
  expect(screen.getByLabelText('Education stage')).toHaveValue('undergraduate');
  expect(screen.getByLabelText('Graduation year')).toHaveValue(2027);
  expect(screen.getByLabelText('Current skill level')).toHaveValue('intermediate');
  expect(screen.getByLabelText('Preferred pace')).toHaveValue('steady');
  expect(screen.getByLabelText('Known skills')).toHaveValue('python, sql');
  expect(screen.getByLabelText('Learning mode: video')).toBeChecked();
  expect(screen.getByLabelText('Learning mode: text')).not.toBeChecked();
  expect(screen.getByLabelText('College name')).toHaveValue('IIT Example');
  expect(screen.getByLabelText('Branch')).toHaveValue('CSE');
  expect(screen.getByLabelText('College ID')).toHaveValue('C42');
});

test('save PATCHes /api/me/profile', async () => {
  const { calls } = setup({ 'PATCH /api/me/profile': init => ({ body: JSON.parse(String(init?.body)) }) });
  await waitFor(() => expect(screen.getByLabelText('Constraints')).toHaveValue('Evenings only'));
  await userEvent.clear(screen.getByLabelText('Constraints'));
  await userEvent.type(screen.getByLabelText('Constraints'), 'Mornings only');
  await userEvent.click(screen.getByRole('button', { name: /save profile/i }));
  await waitFor(() => {
    const patch = calls.find(c => c.method === 'PATCH' && c.path === '/api/me/profile');
    expect(patch).toBeTruthy();
    const body = JSON.parse(String(patch?.init?.body));
    expect(body).toMatchObject({
      education_stage: 'undergraduate', graduation_year: 2027, current_skill_level: 'intermediate',
      known_skills: ['python', 'sql'], learning_modes: ['video'], preferred_pace: 'steady',
      constraints: 'Mornings only', college_name: 'IIT Example', college_year: '3', branch: 'CSE', college_id: 'C42',
    });
  });
});

test('delete requires typing DELETE', async () => {
  const { calls } = setup({ 'DELETE /api/me': { status: 204 } });
  await waitFor(() => expect(screen.getByLabelText('Constraints')).toHaveValue('Evenings only'));
  await userEvent.click(screen.getByRole('button', { name: /delete account/i }));
  const confirmButton = screen.getByRole('button', { name: /delete my account/i });
  expect(confirmButton).toBeDisabled();
  await userEvent.type(screen.getByLabelText('Type DELETE to confirm'), 'DEL');
  expect(confirmButton).toBeDisabled();
  await userEvent.type(screen.getByLabelText('Type DELETE to confirm'), 'ETE');
  expect(confirmButton).toBeEnabled();
  await userEvent.click(confirmButton);
  await waitFor(() => expect(calls.some(c => c.method === 'DELETE' && c.path === '/api/me')).toBe(true));
});
