import { screen } from '@testing-library/react';
import App from './App';
import { AuthProvider } from './auth/AuthProvider';
import { mockFetch } from './test/mockFetch';
import { renderWithProviders } from './test/render';

test('unauthenticated visitor is redirected to the login page', async () => {
  mockFetch({});
  renderWithProviders(<AuthProvider><App /></AuthProvider>);
  expect(await screen.findByRole('heading', { name: 'Sign in to your learning space' })).toBeInTheDocument();
});
