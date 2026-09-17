import { vi } from 'vitest';

export type Route = { status?: number; body?: unknown; headers?: Record<string, string> } | ((init?: RequestInit) => { status?: number; body?: unknown });

/** mockFetch({ 'GET /api/auth/me': { body: {...} }, 'POST /api/goals': (init) => ({ body: JSON.parse(init.body) }) }) */
export function mockFetch(routes: Record<string, Route>) {
  const calls: { method: string; path: string; init?: RequestInit }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    const path = url.replace(/^https?:\/\/[^/]+/, '').split('?')[0];
    const method = (init?.method || 'GET').toUpperCase();
    calls.push({ method, path, init });
    const route = routes[`${method} ${path}`];
    if (!route) return new Response(JSON.stringify({ detail: `no mock for ${method} ${path}` }), { status: 404, headers: { 'content-type': 'application/json' } });
    const resolved = typeof route === 'function' ? route(init) : route;
    return new Response(resolved.body === undefined ? '' : JSON.stringify(resolved.body), { status: resolved.status ?? 200, headers: { 'content-type': 'application/json', ...(('headers' in resolved && resolved.headers) || {}) } });
  });
  globalThis.fetch = fn as unknown as typeof fetch;
  return { fn, calls };
}
