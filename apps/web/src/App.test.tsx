import { screen } from '@testing-library/react';
import App from './App';
import { renderWithProviders } from './test/render';

test('renders the shell title', () => {
  renderWithProviders(<App />);
  expect(screen.getByRole('heading', { name: 'StudyOS' })).toBeInTheDocument();
});
