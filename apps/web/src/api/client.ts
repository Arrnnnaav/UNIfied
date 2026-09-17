import { clearToken, getToken } from '@/auth/storage';

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) { super(message); this.name = 'ApiError'; }
}

let unauthorizedHandler: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => { unauthorizedHandler = fn; };

export const apiBase = () => (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

function headers(json: boolean): Record<string, string> {
  const h: Record<string, string> = {};
  if (json) h['Content-Type'] = 'application/json';
  const token = getToken();
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

async function toError(response: Response): Promise<ApiError> {
  const data = await response.json().catch(() => ({}));
  const detail = data.detail;
  if (detail && typeof detail === 'object' && detail.code) return new ApiError(detail.code, detail.message || 'request failed', response.status);
  const message = typeof detail === 'string' ? detail : data.message || `request failed (${response.status})`;
  return new ApiError(response.status === 401 ? 'AUTH_REQUIRED' : 'ERROR', message, response.status);
}

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init;
  let response: Response;
  try {
    response = await fetch(apiBase() + path, { ...rest, headers: { ...headers(json !== undefined), ...(rest.headers as Record<string, string>) }, body: json !== undefined ? JSON.stringify(json) : rest.body });
  } catch {
    throw new ApiError('NETWORK', `API unreachable at ${apiBase() || window.location.origin}`, 0);
  }
  if (response.status === 401) { clearToken(); unauthorizedHandler(); }
  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  const type = response.headers.get('content-type') || '';
  return (type.includes('json') ? response.json() : response.text()) as Promise<T>;
}

/** POST that returns the raw streaming Response (SSE); caller reads body with readSse. */
export async function apiStream(path: string, json: unknown, signal?: AbortSignal): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(apiBase() + path, { method: 'POST', headers: headers(true), body: JSON.stringify(json), signal });
  } catch (err) {
    if (signal?.aborted || (err as { name?: string })?.name === 'AbortError') throw err;
    throw new ApiError('NETWORK', `API unreachable at ${apiBase() || window.location.origin}`, 0);
  }
  if (response.status === 401) { clearToken(); unauthorizedHandler(); }
  if (!response.ok) throw await toError(response);
  return response;
}
