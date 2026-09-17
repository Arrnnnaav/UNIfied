import { api, apiStream, ApiError, setUnauthorizedHandler } from './client';
import { setToken } from '@/auth/storage';
import { mockFetch } from '@/test/mockFetch';

test('adds bearer and json headers, parses json', async () => {
  setToken('tok');
  const { calls } = mockFetch({ 'POST /api/goals': (init) => ({ body: { echoed: JSON.parse(String(init?.body)) } }) });
  const out = await api<{ echoed: { title: string } }>('/api/goals', { method: 'POST', json: { title: 'x' } });
  expect(out.echoed.title).toBe('x');
  const headers = calls[0].init?.headers as Record<string, string>;
  expect(headers.Authorization).toBe('Bearer tok');
  expect(headers['Content-Type']).toBe('application/json');
});

test('normalises string and object details into ApiError', async () => {
  mockFetch({ 'GET /a': { status: 404, body: { detail: 'goal not found' } }, 'GET /b': { status: 429, body: { detail: { code: 'RATE_LIMITED', message: 'slow down' } } } });
  await expect(api('/a')).rejects.toMatchObject({ code: 'ERROR', message: 'goal not found', status: 404 });
  await expect(api('/b')).rejects.toMatchObject({ code: 'RATE_LIMITED', message: 'slow down' });
});

test('401 clears token and calls the unauthorized handler', async () => {
  setToken('stale');
  const handler = vi.fn();
  setUnauthorizedHandler(handler);
  mockFetch({ 'GET /api/auth/me': { status: 401, body: { detail: 'authentication required' } } });
  await expect(api('/api/auth/me')).rejects.toBeInstanceOf(ApiError);
  expect(localStorage.getItem('studyos_token')).toBeNull();
  expect(handler).toHaveBeenCalled();
});

test('apiStream converts a rejected fetch into a NETWORK ApiError', async () => {
  globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
  await expect(apiStream('/api/x', {}, undefined)).rejects.toMatchObject({ code: 'NETWORK' });
});
