# StudyOS Web App (React) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-file static shell with a React app (`apps/web`) that has real login/register/sign-out, an onboarding wizard, every student surface, and a separate role-gated operator panel, styled with the "candlelit ink" token set, deployable to AWS Amplify.

**Architecture:** Vite + React + TS SPA talks to the existing FastAPI API over `fetch` with a bearer token. `AuthProvider` loads `/api/auth/me`; route guards derive from it. Each route is a feature folder (page + hooks). TanStack Query owns server state; SSE responses are read with `fetch` + `ReadableStream`.

**Tech Stack:** Vite 5, React 18, TypeScript 5, Tailwind 3, React Router 6, TanStack Query 5, Vitest 2 + @testing-library/react, Node 20. Backend: FastAPI (Python 3.12, pytest).

**Spec:** `docs/superpowers/specs/2026-09-18-studyos-web-app-design.md`

## Global Constraints

- Package root `apps/web`; no UI component library; dark theme only.
- Tokens exactly: bg `#16120d`, surface `#1e1811`, surface2 `#292116`, surface3 `#382c1c`, accent `#8fb89a`, accent-tint `#22301f`, accent-strong `#b8dcc0`, accent2 `#d7929c`, accent2-tint `#3a2228`, text `#f1e7d6`, text-dim `#c2b39c`, text-muted `#8a7c66`, ok `#8fb89a`, yellow `#e0b969`, red `#e08a8a`, border `rgba(241,231,214,.10)`, border-strong `rgba(241,231,214,.20)`, radius 4px, shadow `0 10px 26px rgba(0,0,0,.4)`; fonts Fraunces (display), Work Sans (body), IBM Plex Mono (mono).
- Token in `localStorage.studyos_token`. Web app never sends `X-Device-ID`.
- Backend roles are exactly `student | operator | anonymous`. Operator guard: `role === "operator"`.
- Query keys are arrays; invalidate by prefix.
- Every task ends with tests passing and a commit. Commit messages end with:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01HS5ioeqfj4VhX4ZsiLBrp6`.
- Run backend tests from `services/api` with `py -3.12 -m pytest -q`; frontend with `npm test` in `apps/web`.

## File Structure

```
services/api/app/main.py                 add GET /api/auth/me; CORS reads settings.web_origins
services/api/app/core/config.py          add web_origins: str
services/api/tests/test_auth_me.py       new
apps/web/package.json, vite.config.ts, tailwind.config.ts, postcss.config.js, tsconfig.json, index.html, amplify.yml
apps/web/src/main.tsx                    QueryClientProvider + AuthProvider + RouterProvider
apps/web/src/App.tsx                     route table
apps/web/src/styles.css                  @tailwind, fonts, grain, base
apps/web/src/api/client.ts               api<T>(path, init) / ApiError / apiBase()
apps/web/src/api/sse.ts                  readSse(body, onEvent, signal)
apps/web/src/api/types.ts                Me, Dashboard, Goal, Topic, Session, SpatialContext, ...
apps/web/src/auth/storage.ts             getToken/setToken/clearToken
apps/web/src/auth/AuthProvider.tsx       useAuth(): {me, loading, refresh, signOut}
apps/web/src/auth/guards.tsx             RequireStudent, RequireOperator, RedirectIfSignedIn
apps/web/src/components/*.tsx            Button Card Stat Tag Field Select Table EmptyState Toast Modal Spinner PageHeader
apps/web/src/layouts/AppLayout.tsx       student sidebar + topbar
apps/web/src/layouts/OperatorLayout.tsx  operator topbar + tabs
apps/web/src/features/auth/{LoginPage,RegisterPage,OperatorLoginPage}.tsx
apps/web/src/features/onboarding/OnboardingPage.tsx
apps/web/src/features/today/TodayPage.tsx        + useDashboard.ts
apps/web/src/features/roadmap/RoadmapPage.tsx
apps/web/src/features/resources/ResourcesPage.tsx
apps/web/src/features/tutor/TutorPage.tsx        + useTutorStream.ts
apps/web/src/features/pointask/PointAskPage.tsx
apps/web/src/features/milestones/MilestonesPage.tsx
apps/web/src/features/monitoring/MonitoringPage.tsx
apps/web/src/features/profile/ProfilePage.tsx
apps/web/src/features/operator/{OverviewPage,UsersPage,ResourcesPage,SpatialPage,PackagesPage,AnalyticsPage,MonitoringPage}.tsx + useOperator.ts
apps/web/src/test/setup.ts, mockFetch.ts, render.tsx
apps/web/src/**/*.test.tsx
scripts/deploy_aws.ps1                   -WebOrigin param -> WEB_ORIGINS
scripts/package_extension.py             --dashboard-url
apps/extension/manifest.json             detect.js matches *.amplifyapp.com
Makefile                                  build-web / test-web targets
docs/WEB_APP.md                          how to run/build/deploy
```

---

### Task 1: Backend — `GET /api/auth/me` and `WEB_ORIGINS`

**Files:**
- Modify: `services/api/app/core/config.py` (Settings class)
- Modify: `services/api/app/main.py` (CORS middleware ~line 324; add route after `/api/auth/login`)
- Test: `services/api/tests/test_auth_me.py`

**Interfaces:**
- Produces: `GET /api/auth/me` → `{id, name, email, role, student_id, has_goals, profile_complete}`; 401 without token in production, demo student in development.
- Produces: `Settings.web_origins: str` (comma list) merged into CORS `allow_origins`.

- [ ] **Step 1: Write the failing test**

```python
# services/api/tests/test_auth_me.py
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from fastapi.testclient import TestClient

from app.main import app


def test_me_reports_onboarding_state_and_role():
    with TestClient(app) as client:
        email = f"me-{uuid.uuid4().hex[:8]}@example.com"
        registered = client.post("/api/auth/register", json={"name": "Me", "email": email, "password": "a-secure-password"}).json()
        auth = {"Authorization": "Bearer " + registered["access_token"]}
        me = client.get("/api/auth/me", headers=auth).json()
        assert me["email"] == email and me["role"] == "student" and me["has_goals"] is False and me["profile_complete"] is False
        client.patch("/api/me/profile", json={"education_stage": "undergraduate"}, headers=auth)
        client.post("/api/goals", json={"title": "Learn linear algebra"}, headers=auth)
        me = client.get("/api/auth/me", headers=auth).json()
        assert me["has_goals"] is True and me["profile_complete"] is True and me["student_id"]


def test_me_rejects_bad_token():
    with TestClient(app) as client:
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_cors_allows_configured_web_origin(monkeypatch):
    from app.main import settings
    assert "http://localhost:5173" in settings.web_origins
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/api && py -3.12 -m pytest tests/test_auth_me.py -q`
Expected: FAIL — 404 on `/api/auth/me`, AttributeError `web_origins`.

- [ ] **Step 3: Implement**

`services/api/app/core/config.py`, inside `Settings` next to `jwt_secret_key`:

```python
    # Browser origins allowed to call the API (React app on Vite dev server / Amplify). Comma separated.
    web_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
```

`services/api/app/main.py` — replace the CORS line:

```python
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.web_origins.split(",") if o.strip()],
                   allow_origin_regex=r"^(chrome|moz)-extension://.*$", allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
```

Add after the `login` route:

```python
@app.get("/api/auth/me")
def auth_me(request: Request, db: Session = Depends(get_db)):
    """Who am I + onboarding state; the web app decides login/onboarding/app from this alone."""
    user = current_user(db, request)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    profile_complete = bool(profile and (profile.education_stage not in {"", "other"} or profile.college_name or profile.college_year or profile.branch))
    has_goals = db.scalar(select(Goal.id).where(Goal.owner_id == user.id).limit(1)) is not None
    return {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role, "student_id": user.student_id,
            "has_goals": has_goals, "profile_complete": profile_complete}
```

- [ ] **Step 4: Run tests**

Run: `cd services/api && py -3.12 -m pytest -q`
Expected: all pass (19 existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add services/api/app/core/config.py services/api/app/main.py services/api/tests/test_auth_me.py
git commit -m "feat(api): /api/auth/me and WEB_ORIGINS for the React app"
```

---

### Task 2: Scaffold `apps/web` with tokens, fonts, test harness

**Files:**
- Create: `apps/web/package.json`, `vite.config.ts`, `tailwind.config.ts`, `postcss.config.js`, `tsconfig.json`, `tsconfig.node.json`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/styles.css`, `src/vite-env.d.ts`, `src/test/setup.ts`, `src/test/render.tsx`, `src/test/mockFetch.ts`, `src/App.test.tsx`, `.gitignore`
- Modify: `Makefile` (add `build-web`, `test-web`)

**Interfaces:**
- Produces: `renderWithProviders(ui, {route})` test helper; `mockFetch(routes)` helper that stubs `globalThis.fetch` with `{ 'GET /api/auth/me': {status, body} }` entries.
- Produces: Tailwind classes `bg-bg bg-surface bg-surface2 bg-surface3 text-text text-dim text-muted text-accent text-accent2 border-line border-strong font-display font-body font-mono`.

- [ ] **Step 1: Create the package**

```bash
mkdir -p apps/web/src/test && cd apps/web
npm init -y >/dev/null
npm i react@18 react-dom@18 react-router-dom@6 @tanstack/react-query@5
npm i -D vite@5 @vitejs/plugin-react typescript@5 tailwindcss@3 postcss autoprefixer vitest@2 jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom @types/react @types/react-dom
```

`apps/web/package.json` scripts (replace the `scripts` block):

```json
"scripts": {
  "dev": "vite",
  "build": "tsc --noEmit && vite build",
  "preview": "vite preview --port 4173",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

`apps/web/.gitignore`: `node_modules\ndist\n`

- [ ] **Step 2: Config files**

`apps/web/vite.config.ts`:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'], globals: true, css: false },
});
```

`apps/web/tailwind.config.ts`:

```ts
import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#16120d', surface: '#1e1811', surface2: '#292116', surface3: '#382c1c',
        accent: { DEFAULT: '#8fb89a', tint: '#22301f', strong: '#b8dcc0' },
        accent2: { DEFAULT: '#d7929c', tint: '#3a2228' },
        text: '#f1e7d6', dim: '#c2b39c', muted: '#8a7c66',
        ok: '#8fb89a', yellow: '#e0b969', red: '#e08a8a',
        line: 'rgba(241,231,214,.10)', strong: 'rgba(241,231,214,.20)',
      },
      fontFamily: { display: ['Fraunces', 'Georgia', 'serif'], body: ['"Work Sans"', 'system-ui', 'sans-serif'], mono: ['"IBM Plex Mono"', 'monospace'] },
      borderRadius: { DEFAULT: '4px' },
      boxShadow: { card: '0 10px 26px rgba(0,0,0,.4)' },
    },
  },
  plugins: [],
} satisfies Config;
```

`apps/web/postcss.config.js`: `export default { plugins: { tailwindcss: {}, autoprefixer: {} } };`

`apps/web/tsconfig.json`:

```json
{ "compilerOptions": { "target": "ES2022", "lib": ["ES2022", "DOM", "DOM.Iterable"], "module": "ESNext", "moduleResolution": "Bundler",
  "jsx": "react-jsx", "strict": true, "noUnusedLocals": true, "skipLibCheck": true, "types": ["vitest/globals", "@testing-library/jest-dom"],
  "baseUrl": ".", "paths": { "@/*": ["src/*"] } }, "include": ["src"] }
```

Add to `vite.config.ts` top: `import path from 'node:path';` and inside `defineConfig`: `resolve: { alias: { '@': path.resolve(__dirname, 'src') } },`.

`apps/web/index.html`:

```html
<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>StudyOS</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
</head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>
```

`apps/web/src/styles.css`:

```css
@tailwind base; @tailwind components; @tailwind utilities;

:root { color-scheme: dark; }
body { @apply bg-bg text-text font-body text-[15px] leading-[1.55] min-h-screen; }
/* paper grain, as in tracker: this is a page, not a screen */
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .5;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='matrix' values='0 0 0 0 0.16  0 0 0 0 0.14  0 0 0 0 0.11  0 0 0 0.04 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
#root { position: relative; z-index: 1; }
h1, h2, h3 { @apply font-display font-normal; }
:focus-visible { @apply outline outline-2 outline-accent2 outline-offset-2; }
.label { @apply text-[11px] tracking-[.14em] uppercase text-muted font-semibold; }
.rule { @apply border-b-2 border-text; }
```

`apps/web/src/vite-env.d.ts`: `/// <reference types="vite/client" />`

- [ ] **Step 3: Minimal app + test harness**

`apps/web/src/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './styles.css';

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10_000 } } });

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter><App /></BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
```

`apps/web/src/App.tsx` (placeholder until Task 4):

```tsx
export default function App() {
  return <main className="p-8"><h1 className="text-3xl">StudyOS</h1><p className="text-dim">Loading shell…</p></main>;
}
```

`apps/web/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => { cleanup(); localStorage.clear(); });
```

`apps/web/src/test/mockFetch.ts`:

```ts
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
```

`apps/web/src/test/render.tsx`:

```tsx
import { ReactElement } from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

export function renderWithProviders(ui: ReactElement, { route = '/' }: { route?: string } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter></QueryClientProvider>);
}
```

`apps/web/src/App.test.tsx`:

```tsx
import { screen } from '@testing-library/react';
import App from './App';
import { renderWithProviders } from './test/render';

test('renders the shell title', () => {
  renderWithProviders(<App />);
  expect(screen.getByRole('heading', { name: 'StudyOS' })).toBeInTheDocument();
});
```

- [ ] **Step 4: Run**

Run: `cd apps/web && npm test && npm run build`
Expected: 1 test passes; `dist/` produced.

- [ ] **Step 5: Makefile targets**

Append to `Makefile`:

```make
build-web:
	cd apps/web && npm ci && npm run build

test-web:
	cd apps/web && npm test
```

- [ ] **Step 6: Commit**

```bash
git add apps/web Makefile
git commit -m "feat(web): scaffold React app with candlelit-ink tokens and test harness"
```

---

### Task 3: API client, SSE reader, auth storage

**Files:**
- Create: `apps/web/src/api/client.ts`, `apps/web/src/api/sse.ts`, `apps/web/src/api/types.ts`, `apps/web/src/auth/storage.ts`
- Test: `apps/web/src/api/client.test.ts`, `apps/web/src/api/sse.test.ts`

**Interfaces:**
- Produces: `api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T>`; `class ApiError extends Error { code: string; status: number }`; `apiBase(): string`; `apiStream(path, json, signal): Promise<Response>`.
- Produces: `readSse(body: ReadableStream<Uint8Array>, onEvent: (name: string, data: any) => void, signal?: AbortSignal): Promise<void>`.
- Produces: `getToken(): string | null`, `setToken(t)`, `clearToken()`, `onUnauthorized: () => void` (settable hook used by AuthProvider).

- [ ] **Step 1: Failing tests**

`apps/web/src/api/client.test.ts`:

```ts
import { api, ApiError, setUnauthorizedHandler } from './client';
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
```

`apps/web/src/api/sse.test.ts`:

```ts
import { readSse } from './sse';

function stream(chunks: string[]) {
  const enc = new TextEncoder();
  return new ReadableStream<Uint8Array>({ start(c) { chunks.forEach(ch => c.enqueue(enc.encode(ch))); c.close(); } });
}

test('parses events split across chunks', async () => {
  const events: [string, unknown][] = [];
  await readSse(stream(['event: status\ndata: {"status":"x"}\n\nevent: del', 'ta\ndata: {"text":"hi"}\n\n']), (n, d) => events.push([n, d]));
  expect(events).toEqual([['status', { status: 'x' }], ['delta', { text: 'hi' }]]);
});
```

- [ ] **Step 2: Run — expect FAIL (modules missing)**

Run: `cd apps/web && npm test`

- [ ] **Step 3: Implement**

`apps/web/src/auth/storage.ts`:

```ts
const KEY = 'studyos_token';
export const getToken = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
export const setToken = (token: string) => { try { localStorage.setItem(KEY, token); } catch { /* private mode */ } };
export const clearToken = () => { try { localStorage.removeItem(KEY); } catch { /* ignore */ } };
```

`apps/web/src/api/client.ts`:

```ts
import { clearToken, getToken } from '@/auth/storage';

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) { super(message); }
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
  const response = await fetch(apiBase() + path, { method: 'POST', headers: headers(true), body: JSON.stringify(json), signal });
  if (response.status === 401) { clearToken(); unauthorizedHandler(); }
  if (!response.ok) throw await toError(response);
  return response;
}
```

`apps/web/src/api/sse.ts`:

```ts
/** Read `event: name\ndata: json\n\n` blocks from a fetch body. Resolves when the stream ends or the signal aborts. */
export async function readSse(body: ReadableStream<Uint8Array>, onEvent: (name: string, data: any) => void, signal?: AbortSignal): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const onAbort = () => reader.cancel().catch(() => {});
  signal?.addEventListener('abort', onAbort);
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';
      for (const block of blocks) {
        const match = block.match(/^event: (.+)\ndata: (.+)$/s);
        if (!match) continue;
        let data: unknown = match[2];
        try { data = JSON.parse(match[2]); } catch { /* keep raw */ }
        onEvent(match[1].trim(), data);
      }
    }
  } finally {
    signal?.removeEventListener('abort', onAbort);
  }
}
```

`apps/web/src/api/types.ts`:

```ts
export type Role = 'student' | 'operator' | 'anonymous';
export interface Me { id: string; name: string; email: string; role: Role; student_id: string | null; has_goals: boolean; profile_complete: boolean }
export interface AuthResponse { access_token: string; token_type: string; user: { id: string; student_id: string | null; name: string; role: Role }; adopted_marks?: number }
export interface Topic { id: string; title: string; description: string; difficulty: string; estimated_minutes: number; progress: number; mastery: number; phase_id: string; resource_count: number }
export interface Phase { id: string; title: string; order_index: number; topics: Topic[] }
export interface Goal { id: string; title: string; goal_type: string; target_date: string | null; weekly_hours: number; status: string; phases: Phase[]; resources?: unknown[] }
export interface Session { id: string; goal_id: string; topic_id: string | null; topic: string | null; kind: string; status: string; planned_minutes: number; actual_minutes: number; notes: string; started_at: string | null; completed_at: string | null; created_at: string }
export interface TodayItem { topic_id: string; action: string; kind: string; estimated_minutes: number; priority: string; reason: string; mastery: number; dependencies: string[] }
export interface SpatialReview { id: string; spatial_context_id: string; title: string; minutes: number; reason: string; due_at: string; kind: string }
export interface Dashboard { user: { name: string }; goal: Goal | null; today: TodayItem[]; spatial_reviews: SpatialReview[]; sessions: Session[]; plan_status: Record<string, unknown>; stats: { topics: number; mastered: number; average_mastery: number; [k: string]: unknown } }
export interface SpatialContext { id: string; goal_id: string | null; utterance: string; marks: unknown[]; source: string; confidence: number; review_status: string; page: { url: string; title: string; surface: string }; answer: { text?: string; history?: unknown[]; anchors_used?: { text: string }[]; sources?: { id: number; url: string; title: string }[]; meta?: { provider?: string; model?: string } }; turns: number; created_at: string }
export interface Profile { education_stage: string; graduation_year: number | null; current_skill_level: string; known_skills: string[]; learning_modes: string[]; preferred_pace: string; constraints: string; college_name: string; college_year: string; branch: string; college_id: string }
export interface ReviewItem { id: string; topic_id: string; topic: string; due_at: string; interval_days: number; prompt: string; spatial_context_id: string | null }
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd apps/web && npm test`

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/api apps/web/src/auth/storage.ts
git commit -m "feat(web): api client with error normalisation, SSE reader, token storage"
```

---

### Task 4: AuthProvider, guards, layouts, component kit, router

**Files:**
- Create: `apps/web/src/auth/AuthProvider.tsx`, `apps/web/src/auth/guards.tsx`, `apps/web/src/layouts/AppLayout.tsx`, `apps/web/src/layouts/OperatorLayout.tsx`, `apps/web/src/components/{Button,Card,Stat,Tag,Field,Select,Table,EmptyState,Toast,Modal,Spinner,PageHeader}.tsx`, `apps/web/src/components/index.ts`, `apps/web/src/features/NotFoundPage.tsx`
- Modify: `apps/web/src/App.tsx`, `apps/web/src/main.tsx`
- Test: `apps/web/src/auth/guards.test.tsx`

**Interfaces:**
- Produces: `useAuth(): { me: Me | null; loading: boolean; error: ApiError | null; refresh(): Promise<void>; signOut(): void }`.
- Produces: `<RequireStudent/>`, `<RequireOperator/>`, `<RedirectIfSignedIn/>` as `<Outlet/>`-based route wrappers.
- Produces: `useToast(): { push(message: string, kind?: 'ok' | 'error') }` via `ToastProvider`.
- Produces: components with props: `Button({variant?: 'primary'|'ghost'|'danger', size?: 'sm'|'md', loading?})`, `Card({title?, eyebrow?, actions?, children})`, `Stat({label, value, hint?})`, `Tag({tone?: 'accent'|'accent2'|'muted'|'yellow'|'red'})`, `Field({label, hint?, error?, children})`, `Select`, `Table({columns: {key, header, render?}[], rows, empty?})`, `EmptyState({title, body, action?})`, `Modal({open, title, onClose, children})`, `Spinner`, `PageHeader({eyebrow, title, subtitle?, actions?})`.

- [ ] **Step 1: Failing guard tests**

`apps/web/src/auth/guards.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement auth**

`apps/web/src/auth/AuthProvider.tsx`:

```tsx
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, setUnauthorizedHandler } from '@/api/client';
import type { Me } from '@/api/types';
import { clearToken, getToken } from './storage';

interface AuthState { me: Me | null; loading: boolean; error: ApiError | null; refresh: () => Promise<void>; signOut: () => void }
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const hasToken = Boolean(getToken());
  const query = useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/api/auth/me'), enabled: hasToken, retry: false });
  useEffect(() => { setUnauthorizedHandler(() => { client.setQueryData(['me'], null); client.removeQueries({ queryKey: ['me'] }); }); }, [client]);
  const refresh = useCallback(async () => { await client.invalidateQueries({ queryKey: ['me'] }); }, [client]);
  const signOut = useCallback(() => { clearToken(); client.clear(); window.location.assign('/login'); }, [client]);
  const value = useMemo<AuthState>(() => ({
    me: hasToken && !query.isError ? (query.data ?? null) : null,
    loading: hasToken && query.isPending,
    error: (query.error as ApiError) ?? null, refresh, signOut,
  }), [hasToken, query.data, query.isPending, query.isError, query.error, refresh, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth outside AuthProvider');
  return ctx;
}
```

`apps/web/src/auth/guards.tsx`:

```tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import { Spinner } from '@/components';
import { Button } from '@/components';

function Loading() { return <div className="grid place-items-center min-h-screen"><Spinner /></div>; }

/** Any signed-in account. Students without a goal are sent to onboarding (except when already there). */
export function RequireStudent() {
  const { me, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Loading />;
  if (!me) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  if (!me.has_goals && location.pathname !== '/onboarding') return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}

export function RequireOperator() {
  const { me, loading, signOut } = useAuth();
  if (loading) return <Loading />;
  if (!me) return <Navigate to="/operator/login" replace />;
  if (me.role !== 'operator') {
    return (
      <div className="grid place-items-center min-h-screen p-6">
        <div className="bg-surface border border-line p-6 max-w-md">
          <p className="label">Operator</p>
          <h1 className="text-2xl mt-1">This account is not an operator</h1>
          <p className="text-dim mt-2">Signed in as {me.email} ({me.role}). Operator access is granted by an existing operator.</p>
          <div className="mt-4 flex gap-2"><Button onClick={signOut} variant="ghost">Sign out</Button><Button onClick={() => window.location.assign('/')}>Go to StudyOS</Button></div>
        </div>
      </div>
    );
  }
  return <Outlet />;
}

/** Login/register pages bounce signed-in users to the app. */
export function RedirectIfSignedIn() {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  if (me) return <Navigate to={me.role === 'operator' ? '/operator' : '/'} replace />;
  return <Outlet />;
}
```

- [ ] **Step 4: Component kit**

`apps/web/src/components/Button.tsx`:

```tsx
import { ButtonHTMLAttributes } from 'react';
type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger'; size?: 'sm' | 'md'; loading?: boolean };
const styles = { primary: 'bg-accent text-bg hover:bg-accent-strong', ghost: 'bg-transparent border border-strong text-text hover:bg-surface2', danger: 'bg-transparent border border-red text-red hover:bg-red/10' };
export function Button({ variant = 'primary', size = 'md', loading, className = '', children, disabled, ...rest }: Props) {
  return (
    <button {...rest} disabled={disabled || loading} className={`inline-flex items-center gap-2 font-semibold rounded transition ${size === 'sm' ? 'px-3 py-1.5 text-[13px]' : 'px-4 py-2 text-[14px]'} disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}>
      {loading ? <span className="animate-pulse">…</span> : null}{children}
    </button>
  );
}
```

`Card.tsx`:

```tsx
import { ReactNode } from 'react';
export function Card({ eyebrow, title, actions, children, className = '' }: { eyebrow?: string; title?: ReactNode; actions?: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <section className={`bg-surface border border-line shadow-card p-5 ${className}`}>
      {(eyebrow || title || actions) && (
        <header className="flex items-start justify-between gap-4 mb-4">
          <div>{eyebrow && <p className="label">{eyebrow}</p>}{title && <h2 className="text-xl mt-1">{title}</h2>}</div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
```

`Stat.tsx`:

```tsx
export function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return <div className="bg-surface2 border border-line p-4"><p className="label">{label}</p><p className="font-mono text-3xl mt-1 text-text">{value}</p>{hint && <p className="text-muted text-[12px] mt-1">{hint}</p>}</div>;
}
```

`Tag.tsx`:

```tsx
import { ReactNode } from 'react';
const tones = { accent: 'bg-accent-tint text-accent', accent2: 'bg-accent2-tint text-accent2', muted: 'bg-surface3 text-dim', yellow: 'bg-yellow/15 text-yellow', red: 'bg-red/15 text-red' };
export function Tag({ tone = 'muted', children }: { tone?: keyof typeof tones; children: ReactNode }) {
  return <span className={`inline-block font-mono text-[11px] tracking-wide px-2 py-0.5 rounded ${tones[tone]}`}>{children}</span>;
}
```

`Field.tsx` + `Select.tsx`:

```tsx
import { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';
const base = 'w-full bg-bg border border-strong rounded px-3 py-2 text-text placeholder:text-muted focus:border-accent';
export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) {
  return <label className="block"><span className="label">{label}</span><div className="mt-1">{children}</div>{error ? <p className="text-red text-[12px] mt-1">{error}</p> : hint ? <p className="text-muted text-[12px] mt-1">{hint}</p> : null}</label>;
}
export function Input(props: InputHTMLAttributes<HTMLInputElement>) { return <input {...props} className={`${base} ${props.className || ''}`} />; }
export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) { return <textarea {...props} className={`${base} min-h-[90px] ${props.className || ''}`} />; }
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) { return <select {...props} className={`${base} ${props.className || ''}`} />; }
```

(Put `Input`, `Textarea`, `Field` in `Field.tsx`; `Select` in `Select.tsx` importing `base` — simplest: define `base` in `Field.tsx` and `export const inputClass = base`.)

`Table.tsx`:

```tsx
import { ReactNode } from 'react';
export interface Column<Row> { key: string; header: string; render?: (row: Row) => ReactNode; className?: string }
export function Table<Row extends Record<string, any>>({ columns, rows, empty = 'Nothing here yet.', rowKey = (r: Row) => String(r.id) }: { columns: Column<Row>[]; rows: Row[]; empty?: string; rowKey?: (r: Row) => string }) {
  if (!rows.length) return <p className="text-muted text-[13px] py-6 text-center">{empty}</p>;
  return (
    <div className="overflow-x-auto"><table className="w-full text-[14px]">
      <thead><tr className="rule">{columns.map(c => <th key={c.key} className={`label text-left py-2 pr-4 ${c.className || ''}`}>{c.header}</th>)}</tr></thead>
      <tbody>{rows.map(r => <tr key={rowKey(r)} className="border-b border-line">{columns.map(c => <td key={c.key} className={`py-2 pr-4 align-top ${c.className || ''}`}>{c.render ? c.render(r) : String(r[c.key] ?? '')}</td>)}</tr>)}</tbody>
    </table></div>
  );
}
```

`EmptyState.tsx`, `Spinner.tsx`, `PageHeader.tsx`, `Modal.tsx`, `Toast.tsx`:

```tsx
// EmptyState.tsx
import { ReactNode } from 'react';
export function EmptyState({ title, body, action }: { title: string; body?: string; action?: ReactNode }) {
  return <div className="border border-dashed border-strong p-8 text-center"><h3 className="text-lg">{title}</h3>{body && <p className="text-dim mt-1">{body}</p>}{action && <div className="mt-4 inline-flex">{action}</div>}</div>;
}
// Spinner.tsx
export function Spinner() { return <span role="status" aria-label="loading" className="inline-block w-5 h-5 border-2 border-strong border-t-accent rounded-full animate-spin" />; }
// PageHeader.tsx
import { ReactNode } from 'react';
export function PageHeader({ eyebrow, title, subtitle, actions }: { eyebrow: string; title: string; subtitle?: string; actions?: ReactNode }) {
  return <header className="flex items-end justify-between gap-4 mb-6 pb-4 rule"><div><p className="label">{eyebrow}</p><h1 className="text-3xl mt-1">{title}</h1>{subtitle && <p className="text-dim mt-1">{subtitle}</p>}</div>{actions && <div className="flex gap-2">{actions}</div>}</header>;
}
// Modal.tsx
import { ReactNode, useEffect } from 'react';
export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => { if (!open) return; const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose(); window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey); }, [open, onClose]);
  if (!open) return null;
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}><div role="dialog" aria-label={title} className="bg-surface border border-strong shadow-card p-6 w-full max-w-lg" onClick={e => e.stopPropagation()}><h2 className="text-xl mb-4">{title}</h2>{children}</div></div>;
}
// Toast.tsx
import { createContext, ReactNode, useCallback, useContext, useState } from 'react';
type Toast = { id: number; message: string; kind: 'ok' | 'error' };
const Ctx = createContext<{ push: (message: string, kind?: 'ok' | 'error') => void } | null>(null);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((message: string, kind: 'ok' | 'error' = 'ok') => { const id = Date.now() + Math.random(); setItems(t => [...t, { id, message, kind }]); setTimeout(() => setItems(t => t.filter(i => i.id !== id)), 5000); }, []);
  return <Ctx.Provider value={{ push }}>{children}<div className="fixed bottom-4 right-4 z-50 grid gap-2">{items.map(t => <div key={t.id} role="alert" className={`px-4 py-2 border font-mono text-[13px] bg-surface ${t.kind === 'error' ? 'border-red text-red' : 'border-accent text-accent'}`}>{t.message}</div>)}</div></Ctx.Provider>;
}
export function useToast() { const ctx = useContext(Ctx); if (!ctx) throw new Error('useToast outside ToastProvider'); return ctx; }
```

`components/index.ts` re-exports all.

- [ ] **Step 5: Layouts**

`apps/web/src/layouts/AppLayout.tsx`:

```tsx
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components';

const NAV = [['/', 'Today', '⌂'], ['/roadmap', 'Roadmap', '▦'], ['/resources', 'Resources', '◈'], ['/tutor', 'Tutor', '✦'], ['/point-and-ask', 'Point & Ask', '⌁'], ['/milestones', 'Milestones', '◆'], ['/monitoring', 'Monitoring', '◉'], ['/profile', 'Profile', '◎']] as const;

export function AppLayout() {
  const { me, signOut } = useAuth();
  const initials = (me?.name || '?').split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase();
  return (
    <div className="min-h-screen flex">
      <aside className="w-[250px] shrink-0 bg-surface border-r border-line flex flex-col p-5">
        <div className="font-display text-2xl flex items-center gap-2"><span className="text-accent">◒</span>StudyOS</div>
        <p className="label mt-8 mb-3">Personal learning system</p>
        <nav className="grid gap-1">
          {NAV.map(([to, label, icon]) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `px-3 py-2 rounded text-[14px] ${isActive ? 'bg-accent-tint text-accent-strong' : 'text-dim hover:bg-surface2 hover:text-text'}`}><span className="mr-2 font-mono">{icon}</span>{label}</NavLink>)}
        </nav>
        <div className="mt-auto pt-4 border-t border-line flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-accent text-bg grid place-items-center font-mono text-[12px] font-semibold">{initials}</div>
          <div className="min-w-0"><p className="truncate text-[14px]">{me?.name}</p><p className="text-muted text-[12px] font-mono">{me?.student_id || me?.email}</p></div>
          <Button variant="ghost" size="sm" onClick={signOut} className="ml-auto">Out</Button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 p-8 max-w-[1200px]"><Outlet /></main>
    </div>
  );
}
```

`apps/web/src/layouts/OperatorLayout.tsx`:

```tsx
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { Button } from '@/components';

const TABS = [['/operator', 'Overview'], ['/operator/users', 'Users'], ['/operator/resources', 'Resources'], ['/operator/spatial', 'Spatial review'], ['/operator/packages', 'Packages'], ['/operator/analytics', 'Analytics'], ['/operator/monitoring', 'Monitoring']] as const;

export function OperatorLayout() {
  const { me, signOut } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="h-[60px] px-6 flex items-center gap-4 bg-surface rule">
        <span className="font-display text-xl"><span className="text-accent2">▣</span> StudyOS</span>
        <span className="label border border-accent2 text-accent2 px-2 py-0.5">Operator</span>
        <nav className="ml-6 flex gap-1">{TABS.map(([to, label]) => <NavLink key={to} to={to} end={to === '/operator'} className={({ isActive }) => `px-3 py-1.5 rounded text-[13px] ${isActive ? 'bg-accent2-tint text-accent2' : 'text-dim hover:text-text'}`}>{label}</NavLink>)}</nav>
        <span className="ml-auto text-muted font-mono text-[12px]">{me?.email}</span>
        <Button variant="ghost" size="sm" onClick={signOut}>Sign out</Button>
      </header>
      <main className="p-8 max-w-[1300px]"><Outlet /></main>
    </div>
  );
}
```

- [ ] **Step 6: Router**

`apps/web/src/App.tsx`:

```tsx
import { Route, Routes } from 'react-router-dom';
import { RedirectIfSignedIn, RequireOperator, RequireStudent } from '@/auth/guards';
import { AppLayout } from '@/layouts/AppLayout';
import { OperatorLayout } from '@/layouts/OperatorLayout';
import { NotFoundPage } from '@/features/NotFoundPage';

const Placeholder = ({ name }: { name: string }) => <h1 className="text-3xl">{name}</h1>;

export default function App() {
  return (
    <Routes>
      <Route element={<RedirectIfSignedIn />}>
        <Route path="/login" element={<Placeholder name="Login" />} />
        <Route path="/register" element={<Placeholder name="Register" />} />
      </Route>
      <Route path="/operator/login" element={<Placeholder name="Operator login" />} />
      <Route element={<RequireStudent />}>
        <Route path="/onboarding" element={<Placeholder name="Onboarding" />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<Placeholder name="Today" />} />
          <Route path="/roadmap" element={<Placeholder name="Roadmap" />} />
          <Route path="/resources" element={<Placeholder name="Resources" />} />
          <Route path="/tutor" element={<Placeholder name="Tutor" />} />
          <Route path="/point-and-ask" element={<Placeholder name="Point & Ask" />} />
          <Route path="/milestones" element={<Placeholder name="Milestones" />} />
          <Route path="/monitoring" element={<Placeholder name="Monitoring" />} />
          <Route path="/profile" element={<Placeholder name="Profile" />} />
        </Route>
      </Route>
      <Route element={<RequireOperator />}>
        <Route element={<OperatorLayout />}>
          <Route path="/operator" element={<Placeholder name="Overview" />} />
          <Route path="/operator/users" element={<Placeholder name="Users" />} />
          <Route path="/operator/resources" element={<Placeholder name="Resources" />} />
          <Route path="/operator/spatial" element={<Placeholder name="Spatial review" />} />
          <Route path="/operator/packages" element={<Placeholder name="Packages" />} />
          <Route path="/operator/analytics" element={<Placeholder name="Analytics" />} />
          <Route path="/operator/monitoring" element={<Placeholder name="Monitoring" />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
```

`NotFoundPage.tsx`: `export function NotFoundPage() { return <div className="grid place-items-center min-h-screen"><div><p className="label">404</p><h1 className="text-3xl">Nothing here</h1><a className="text-accent underline" href="/">Back to StudyOS</a></div></div>; }`

`main.tsx`: wrap `<App/>` in `<AuthProvider>` and `<ToastProvider>` (inside `BrowserRouter`). Update `App.test.tsx` to mock fetch with no token and assert the login placeholder renders at `/login`.

- [ ] **Step 7: Run tests + build — expect pass**

- [ ] **Step 8: Commit**

```bash
git add apps/web
git commit -m "feat(web): auth provider, route guards, layouts, component kit, router skeleton"
```

---

### Task 5: Login, Register, Operator login pages

**Files:**
- Create: `apps/web/src/features/auth/AuthShell.tsx`, `LoginPage.tsx`, `RegisterPage.tsx`, `OperatorLoginPage.tsx`, `useAuthForm.ts`
- Modify: `apps/web/src/App.tsx` (replace placeholders)
- Test: `apps/web/src/features/auth/LoginPage.test.tsx`

**Interfaces:**
- Consumes: `api`, `setToken`, `useAuth().refresh`.
- Produces: `useAuthForm(path: '/api/auth/login' | '/api/auth/register', onDone: (auth: AuthResponse) => void)` → `{ submit(values), pending, error }`.

- [ ] **Step 1: Failing test**

```tsx
// LoginPage.test.tsx
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/auth/AuthProvider';
import { LoginPage } from './LoginPage';
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

test('shows API error inline', async () => {
  mockFetch({ 'POST /api/auth/login': { status: 401, body: { detail: 'invalid credentials' } } });
  renderWithProviders(<AuthProvider><Routes><Route path="/login" element={<LoginPage />} /></Routes></AuthProvider>, { route: '/login' });
  await userEvent.type(screen.getByLabelText(/email/i), 'a@x');
  await userEvent.type(screen.getByLabelText(/password/i), 'wrong-pass');
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
  expect(await screen.findByText('invalid credentials')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement**

`useAuthForm.ts`:

```ts
import { useState } from 'react';
import { api, ApiError } from '@/api/client';
import type { AuthResponse } from '@/api/types';
import { setToken } from '@/auth/storage';

export function useAuthForm(path: '/api/auth/login' | '/api/auth/register', onDone: (auth: AuthResponse) => void) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(values: Record<string, string>) {
    setPending(true); setError(null);
    try { const auth = await api<AuthResponse>(path, { method: 'POST', json: values }); setToken(auth.access_token); onDone(auth); }
    catch (e) { setError(e instanceof ApiError ? e.message : 'Something went wrong'); }
    finally { setPending(false); }
  }
  return { submit, pending, error };
}
```

`AuthShell.tsx` (centered card with brand, used by all three pages):

```tsx
import { ReactNode } from 'react';
export function AuthShell({ eyebrow, title, children, footer }: { eyebrow: string; title: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="min-h-screen grid place-items-center p-6">
      <div className="w-full max-w-md">
        <div className="font-display text-3xl mb-6"><span className="text-accent">◒</span> StudyOS</div>
        <div className="bg-surface border border-line shadow-card p-6"><p className="label">{eyebrow}</p><h1 className="text-2xl mt-1 mb-5">{title}</h1>{children}</div>
        {footer && <p className="text-dim text-[13px] mt-4">{footer}</p>}
      </div>
    </div>
  );
}
```

`LoginPage.tsx`:

```tsx
import { FormEvent, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { Button, Field, Input } from '@/components';
import { AuthShell } from './AuthShell';
import { useAuthForm } from './useAuthForm';

export function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { refresh } = useAuth();
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const { submit, pending, error } = useAuthForm('/api/auth/login', async () => { await refresh(); navigate(params.get('next') || '/', { replace: true }); });
  const onSubmit = (e: FormEvent) => { e.preventDefault(); submit({ email, password }); };
  return (
    <AuthShell eyebrow="Account" title="Sign in to your learning space" footer={<>New here? <Link className="text-accent underline" to="/register">Create an account</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4">
        <Field label="Email or StudyOS ID"><Input value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" required /></Field>
        <Field label="Password" error={error || undefined}><Input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required /></Field>
        <Button type="submit" loading={pending}>Sign in</Button>
      </form>
    </AuthShell>
  );
}
```

`RegisterPage.tsx`: same shape; fields name/email/password (min 8, show hint); `useAuthForm('/api/auth/register', async () => { await refresh(); navigate('/onboarding', { replace: true }); })`; footer links to `/login`.

`OperatorLoginPage.tsx`: `AuthShell eyebrow="Operator" title="Operator sign-in"`; on done: `await refresh(); navigate('/operator', { replace: true })` (the guard shows "not an operator" for students); no register link; footer: "Operators are created with the bootstrap token by an admin."

Wire in `App.tsx`: replace the three placeholders.

- [ ] **Step 4: Run tests — pass. Commit**

```bash
git add apps/web/src/features/auth apps/web/src/App.tsx
git commit -m "feat(web): login, register and operator login pages"
```

---

### Task 6: Onboarding wizard

**Files:**
- Create: `apps/web/src/features/onboarding/OnboardingPage.tsx`
- Modify: `apps/web/src/App.tsx`
- Test: `apps/web/src/features/onboarding/OnboardingPage.test.tsx`

**Interfaces:**
- Consumes: `PATCH /api/me/profile` (Profile fields), `POST /api/goals` `{title, goal_type, weekly_hours, target_date}` → Goal; `useAuth().refresh`.

- [ ] **Step 1: Failing test**

```tsx
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/auth/AuthProvider';
import { setToken } from '@/auth/storage';
import { OnboardingPage } from './OnboardingPage';
import { mockFetch } from '@/test/mockFetch';
import { renderWithProviders } from '@/test/render';

test('skip profile, create goal, land on today', async () => {
  setToken('t');
  let goals = false;
  const { calls } = mockFetch({
    'GET /api/auth/me': () => ({ body: { id: '1', name: 'A', email: 'a@x', role: 'student', student_id: 'S1', has_goals: goals, profile_complete: false } }),
    'POST /api/goals': (init) => { goals = true; return { body: { id: 'g1', ...JSON.parse(String(init?.body)), phases: [] } }; },
  });
  renderWithProviders(<AuthProvider><Routes><Route path="/onboarding" element={<OnboardingPage />} /><Route path="/" element={<p>today page</p>} /></Routes></AuthProvider>, { route: '/onboarding' });
  await userEvent.click(await screen.findByRole('button', { name: /skip/i }));
  await userEvent.type(screen.getByLabelText(/goal title/i), 'Learn linear algebra');
  await userEvent.click(screen.getByRole('button', { name: /create my plan/i }));
  expect(await screen.findByText('today page')).toBeInTheDocument();
  expect(calls.some(c => c.method === 'POST' && c.path === '/api/goals')).toBe(true);
});
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement**

```tsx
// OnboardingPage.tsx
import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { api, ApiError } from '@/api/client';
import type { Goal, Profile } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { Button, Field, Input, Select } from '@/components';
import { AuthShell } from '@/features/auth/AuthShell';

const STAGES = [['school', 'School'], ['undergraduate', 'Undergraduate'], ['postgraduate', 'Postgraduate'], ['professional', 'Working professional'], ['other', 'Other']];
const GOAL_TYPES = [['skill', 'Learn a skill'], ['exam', 'Prepare for an exam'], ['course', 'Finish a course'], ['project', 'Build a project'], ['custom', 'Something else']];

export function OnboardingPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [step, setStep] = useState<1 | 2>(1);
  const [profile, setProfile] = useState({ education_stage: 'undergraduate', college_name: '', college_year: '', branch: '', current_skill_level: 'beginner', preferred_pace: 'steady' });
  const [goal, setGoal] = useState({ title: '', goal_type: 'skill', weekly_hours: 8, target_date: '' });
  const saveProfile = useMutation({ mutationFn: (values: Partial<Profile>) => api<Profile>('/api/me/profile', { method: 'PATCH', json: values }), onSuccess: () => setStep(2) });
  const createGoal = useMutation({
    mutationFn: () => api<Goal>('/api/goals', { method: 'POST', json: { title: goal.title.trim(), goal_type: goal.goal_type, weekly_hours: Number(goal.weekly_hours), target_date: goal.target_date || null } }),
    onSuccess: async () => { await refresh(); navigate('/', { replace: true }); },
  });
  const err = (m: unknown) => (m instanceof ApiError ? m.message : undefined);

  if (step === 1) return (
    <AuthShell eyebrow="Step 1 of 2" title="Tell StudyOS where you are">
      <form className="grid gap-4" onSubmit={(e: FormEvent) => { e.preventDefault(); saveProfile.mutate(profile); }}>
        <Field label="Stage"><Select value={profile.education_stage} onChange={e => setProfile({ ...profile, education_stage: e.target.value })}>{STAGES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="College / school"><Input value={profile.college_name} onChange={e => setProfile({ ...profile, college_name: e.target.value })} /></Field>
          <Field label="Year"><Input value={profile.college_year} onChange={e => setProfile({ ...profile, college_year: e.target.value })} placeholder="2nd year" /></Field>
        </div>
        <Field label="Branch / field"><Input value={profile.branch} onChange={e => setProfile({ ...profile, branch: e.target.value })} placeholder="Computer Science" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Current level"><Select value={profile.current_skill_level} onChange={e => setProfile({ ...profile, current_skill_level: e.target.value })}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></Select></Field>
          <Field label="Pace"><Select value={profile.preferred_pace} onChange={e => setProfile({ ...profile, preferred_pace: e.target.value })}><option value="relaxed">Relaxed</option><option value="steady">Steady</option><option value="intense">Intense</option></Select></Field>
        </div>
        {err(saveProfile.error) && <p className="text-red text-[13px]">{err(saveProfile.error)}</p>}
        <div className="flex gap-2 justify-end"><Button type="button" variant="ghost" onClick={() => setStep(2)}>Skip for now</Button><Button type="submit" loading={saveProfile.isPending}>Continue</Button></div>
      </form>
    </AuthShell>
  );
  return (
    <AuthShell eyebrow="Step 2 of 2" title="What are you learning first?">
      <form className="grid gap-4" onSubmit={(e: FormEvent) => { e.preventDefault(); createGoal.mutate(); }}>
        <Field label="Goal title" hint="Be concrete: “Pass DBMS mid-sem”, “Learn PyTorch basics”"><Input value={goal.title} onChange={e => setGoal({ ...goal, title: e.target.value })} minLength={3} required /></Field>
        <Field label="Type"><Select value={goal.goal_type} onChange={e => setGoal({ ...goal, goal_type: e.target.value })}>{GOAL_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Hours per week"><Input type="number" min={1} max={80} value={goal.weekly_hours} onChange={e => setGoal({ ...goal, weekly_hours: Number(e.target.value) })} /></Field>
          <Field label="Target date (optional)"><Input type="date" value={goal.target_date} onChange={e => setGoal({ ...goal, target_date: e.target.value })} /></Field>
        </div>
        {err(createGoal.error) && <p className="text-red text-[13px]">{err(createGoal.error)}</p>}
        <div className="flex gap-2 justify-end"><Button type="button" variant="ghost" onClick={() => setStep(1)}>Back</Button><Button type="submit" loading={createGoal.isPending}>Create my plan</Button></div>
      </form>
    </AuthShell>
  );
}
```

- [ ] **Step 4: Tests pass → commit** `feat(web): onboarding wizard (profile, first goal)`

---

### Task 7: Today page

**Files:**
- Create: `apps/web/src/features/today/useDashboard.ts`, `TodayPage.tsx`
- Test: `apps/web/src/features/today/TodayPage.test.tsx`

**Interfaces:**
- Produces: `useDashboard()` = `useQuery({ queryKey: ['dashboard'], queryFn: () => api<Dashboard>('/api/dashboard') })`; `useReviewQueue()` = `['review']` → `ReviewItem[]`.
- Consumes: `POST /api/learning-sessions {goal_id, topic_id, kind, planned_minutes}`, `PATCH /api/learning-sessions/{id} {status: 'active'|'completed', actual_minutes?, notes?}`, `POST /api/review/{id}/complete`.

- [ ] **Step 1: Failing test** — render with mocked `/api/dashboard` (stats 4/1/0.5, one today item "Review: Vectors", one spatial review) and `/api/review` → asserts stat "4" topics, the action text, the spatial review title; clicking "Start session" posts to `/api/learning-sessions`.

```tsx
test('shows stats, next actions and starts a session', async () => {
  setToken('t');
  const { calls } = mockFetch({
    'GET /api/auth/me': { body: me },
    'GET /api/dashboard': { body: { user: { name: 'A' }, goal: { id: 'g1', title: 'LA', goal_type: 'skill', target_date: null, weekly_hours: 8, status: 'active', phases: [] }, today: [{ topic_id: 't1', action: 'Review: Vectors', kind: 'review', estimated_minutes: 8, priority: 'high', reason: 'due', mastery: .4, dependencies: [] }], spatial_reviews: [{ id: 'r1', spatial_context_id: 'c1', title: 'Point & Ask: minus sign', minutes: 8, reason: 'you circled', due_at: '2026-09-19T00:00:00', kind: 'spatial_review' }], sessions: [], plan_status: {}, stats: { topics: 4, mastered: 1, average_mastery: .5 } } },
    'GET /api/review': { body: [] },
    'POST /api/learning-sessions': (init) => ({ body: { id: 's1', ...JSON.parse(String(init?.body)), status: 'planned', actual_minutes: 0, notes: '', started_at: null, completed_at: null, created_at: 'now', topic: 'Vectors' } }),
  });
  renderWithProviders(<AuthProvider><ToastProvider><TodayPage /></ToastProvider></AuthProvider>);
  expect(await screen.findByText('Review: Vectors')).toBeInTheDocument();
  expect(screen.getByText('4')).toBeInTheDocument();
  expect(screen.getByText('Point & Ask: minus sign')).toBeInTheDocument();
  await userEvent.click(screen.getAllByRole('button', { name: /start session/i })[0]);
  await waitFor(() => expect(calls.some(c => c.path === '/api/learning-sessions' && c.method === 'POST')).toBe(true));
});
```

- [ ] **Step 2: Run — FAIL. Step 3: Implement**

`useDashboard.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Dashboard, ReviewItem, Session } from '@/api/types';

export const useDashboard = () => useQuery({ queryKey: ['dashboard'], queryFn: () => api<Dashboard>('/api/dashboard') });
export const useReviewQueue = () => useQuery({ queryKey: ['review'], queryFn: () => api<ReviewItem[]>('/api/review') });
export function useSessionActions() {
  const client = useQueryClient();
  const invalidate = () => client.invalidateQueries({ queryKey: ['dashboard'] });
  const start = useMutation({ mutationFn: (body: { goal_id: string; topic_id: string | null; kind: string; planned_minutes: number }) => api<Session>('/api/learning-sessions', { method: 'POST', json: body }), onSuccess: invalidate });
  const update = useMutation({ mutationFn: ({ id, ...body }: { id: string; status: string; actual_minutes?: number; notes?: string }) => api<Session>(`/api/learning-sessions/${id}`, { method: 'PATCH', json: body }), onSuccess: invalidate });
  const completeReview = useMutation({ mutationFn: (id: string) => api(`/api/review/${id}/complete`, { method: 'POST' }), onSuccess: () => { invalidate(); client.invalidateQueries({ queryKey: ['review'] }); } });
  return { start, update, completeReview };
}
```

`TodayPage.tsx` layout: `PageHeader eyebrow="Today" title="Make progress that counts" subtitle="Completion is activity. Mastery is evidence."`; 3 `Stat`s (topics, mastered, avg mastery %); `Card "Next best actions"` listing `today[]` rows with `Tag` priority, reason, `Button "Start session"` → `start.mutate({goal_id: goal.id, topic_id, kind, planned_minutes: estimated_minutes})`; `Card "Point & Ask review"` (only when `spatial_reviews.length`) with `Link to /tutor?spatial=<id>`; `Card "Sessions"` table of `sessions` with Start/Complete buttons (`update.mutate({id, status:'active'})` / `{status:'completed', actual_minutes: planned}`); `Card "Review queue"` from `useReviewQueue` with `Done` → `completeReview`. Loading → `Spinner`; no goal → `EmptyState` linking `/onboarding`.

- [ ] **Step 4: Tests pass → commit** `feat(web): today page`

---

### Task 8: Roadmap page

**Files:** `apps/web/src/features/roadmap/RoadmapPage.tsx`, `useRoadmap.ts`; test `RoadmapPage.test.tsx`.

**Interfaces:**
- Consumes: goal from `useDashboard`; `PATCH /api/topics/{id}/progress {progress: 0|1}`; `POST /api/topics {phase_id, title, description?, estimated_minutes?}`; `POST /api/topics/{id}/assessment {}` → `{id, questions:[{prompt, options?}]}`; `POST /api/assessments/{id}/attempt {answers: string[]}` → `{score, feedback, mastery}`; `GET /api/goals/{id}/coverage`.
- Produces: `useTopicActions()` → `{ setProgress, addTopic, startAssessment, submitAttempt }` mutations invalidating `['dashboard']` and `['goals', goalId, 'coverage']`.

- [ ] **Step 1: Failing test** — mocked dashboard with one phase/two topics; assert phase title and both topics render; toggling a checkbox PATCHes `/api/topics/t1/progress` with `{progress: 1}`.
- [ ] **Step 2: Run — FAIL. Step 3: Implement** — `PageHeader` with goal title + `Tag`s (goal_type, weekly hours, target date); per phase a `Card` with topic rows: checkbox (progress), title, `Tag` difficulty, mono mastery %, `Button size=sm "Quiz"` opens `Modal` that runs `startAssessment` → shows questions with radio/text inputs → `submitAttempt` → shows score/feedback; "Add topic" inline form per phase. Coverage card: `GET coverage` list of objectives with covered/uncovered `Tag`s.
- [ ] **Step 4: Tests pass → commit** `feat(web): roadmap page with progress, quizzes, coverage`

---

### Task 9: Resources page

**Files:** `apps/web/src/features/resources/ResourcesPage.tsx`, `useResources.ts`; test.

**Interfaces:**
- Consumes: `POST /api/resources {goal_id, title, source_type: 'text'|'url'|'github'|'youtube', content?, url?}`; `POST /api/resources/upload` multipart `file`, `goal_id`, `title`; `POST /api/resources/{id}/ingest-url|ingest-github|ingest-youtube {url}`; `GET /api/ingestion/jobs` → `[{id, resource_id, kind, status, progress, error}]`; `GET /api/search?q=&goal_id=` → `[{resource_id, title, snippet, score}]`; resources list from `dashboard.goal.resources` (`[{id,title,source_type,status,trust_status}]`).
- Produces: `useIngestionJobs()` polls every 3 s while any job status is `queued|running`.

- [ ] **Step 1: Failing test** — mocked dashboard with one resource; assert it renders; submit URL form → POST `/api/resources` then `/api/resources/{id}/ingest-url`.
- [ ] **Step 3: Implement** — `PageHeader "Resources"`; left `Card "Add material"` with tabs Paste text / URL / GitHub / YouTube / Upload file (file via `FormData`, `api(path, { method: 'POST', body: form })` — no json header); right `Card "Your library"` table (title, type `Tag`, status, trust `Tag` tone accent for verified / yellow unverified / red rejected); `Card "Ingestion"` job rows with progress bar (`div` width %) and error text; search box → results list with snippet.
- [ ] **Step 4: Tests pass → commit** `feat(web): resources page with ingestion and search`

---

### Task 10: Tutor page (SSE)

**Files:** `apps/web/src/features/tutor/useTutorStream.ts`, `TutorPage.tsx`; test `useTutorStream.test.tsx`.

**Interfaces:**
- Produces: `useTutorStream()` → `{ ask(body: {question, goal_id?, topic_id?, spatial_context_id?}), status: 'idle'|'retrieving'|'done'|'error', answer: {answer: string, citations: {title, snippet}[], evidence?: unknown[]} | null, error: string | null, cancel() }`. Uses `apiStream('/api/tutor/ask/stream', body, signal)` + `readSse`; events `status` → status 'retrieving', `complete` → answer, `error` → `data.detail` (string or `{message}`). Aborts on unmount.
- Consumes: `?spatial=<id>` query param → preselects `spatial_context_id`; `GET /api/spatial-context` for the dropdown.

- [ ] **Step 1: Failing hook test** — mock fetch returning a `Response` whose body is a stream with `status` then `complete {answer:'42', citations:[]}`; `renderHook`, call `ask`, `waitFor(status === 'done')`, assert answer.
- [ ] **Step 3: Implement** — thread UI: message list (question bubbles right, answer left with citations as `Tag`s + expandable snippets), composer with `Textarea` (Enter submits, Shift+Enter newline), `Select` "Use a Point & Ask mark" listing recent marks; status line "Retrieving evidence…"; `Button "Stop"` calls cancel.
- [ ] **Step 4: Tests pass → commit** `feat(web): grounded tutor with SSE`

---

### Task 11: Point & Ask page

**Files:** `apps/web/src/features/pointask/PointAskPage.tsx`, `useSpatial.ts`, `useExtensionDetect.ts`; test.

**Interfaces:**
- Produces: `useSpatial()` = `['spatial']` → `SpatialContext[]`; `useQuizLater()` mutation → `POST /api/spatial-context/{id}/quiz`; `useExtensionDetect(): string | null` reads `document.documentElement.dataset.pointAskExtension` on mount and on a `MutationObserver` of `documentElement` attributes.
- Consumes: `Link to="/tutor?spatial=<id>"`.

- [ ] **Step 1: Failing test** — with `document.documentElement.dataset.pointAskExtension = '0.2.0'` the page shows "Extension installed (v0.2.0)"; without it shows the install steps; a mocked mark renders its page title, question, answer text, and "Quiz me later" POSTs to `/api/spatial-context/c1/quiz`.
- [ ] **Step 3: Implement** — `PageHeader "Point & Ask" "Circle it. Ask it."`; `Card` install/detected (steps: Chrome Web Store link placeholder `https://chrome.google.com/webstore`, hotkey `Alt+Shift+A`); marks list: `Tag` surface, page title link, question, answer excerpt, meta line (provider/model, confidence %, sources count), buttons "Continue in tutor", "Quiz me later" (disabled + "In your review queue" after success).
- [ ] **Step 4: Tests pass → commit** `feat(web): point & ask history and extension detection`

---

### Task 12: Milestones, Monitoring, Profile pages

**Files:** `apps/web/src/features/milestones/MilestonesPage.tsx`, `apps/web/src/features/monitoring/MonitoringPage.tsx`, `apps/web/src/features/profile/ProfilePage.tsx`; one test each.

**Interfaces (from existing API):**
- Milestones: `GET /api/milestones` → `[{id, title, description, achieved_at, goal_id}]`; `POST /api/milestones {goal_id, title, description}`; `POST /api/milestones/{id}/share {recipient_student_id, message}`; `GET /api/milestone-shares` → `[{id, milestone_title, from_name, message, created_at}]`. (Verify exact keys in `serialize_milestone`/share serializer in `main.py` before writing types; adjust `types.ts` accordingly.)
- Monitoring (student): `GET /api/monitoring-dashboards` → `[{id, name, status, role: 'leader'|'member'}]`; `GET /api/monitoring-dashboards/{id}` → `{name, members: [{student_id, name, progress, mastery, on_track, minutes}]}`; `POST /api/monitoring/join/{access_code}`.
- Profile: `GET/PATCH /api/me/profile` (Profile); `GET /api/me/export` → download JSON (use `api<Blob>` via `fetch` + `URL.createObjectURL`); `DELETE /api/me` → then `signOut()`.

- [ ] **Step 1: Failing tests** — milestones: renders a milestone and creating one POSTs; monitoring: join form POSTs `/api/monitoring/join/ABC123`; profile: loads profile into inputs, save PATCHes, delete requires typing `DELETE` in the modal.
- [ ] **Step 3: Implement** — Milestones: two columns (mine with "Share" modal; received shares). Monitoring: join card + my dashboards table + selected dashboard member table (`Tag` ok/yellow for on_track). Profile: form (stage, year, level, pace, modes as checkboxes, known skills comma list, constraints textarea, college fields), "Export my data" ghost button, "Delete account" danger button → `Modal` with confirm input.
- [ ] **Step 4: Tests pass → commit** `feat(web): milestones, monitoring and profile pages`

---

### Task 13: Operator panel pages

**Files:** `apps/web/src/features/operator/useOperator.ts`, `OverviewPage.tsx`, `UsersPage.tsx`, `ResourcesPage.tsx`, `SpatialPage.tsx`, `PackagesPage.tsx`, `AnalyticsPage.tsx`, `MonitoringPage.tsx`; tests `SpatialPage.test.tsx`, `ResourcesPage.test.tsx`.

**Interfaces:**
- Produces: `useOverview()` `['operator','overview']`; `useSnapshot()` `['operator','snapshot']` → `{users, goals, resources, ingestion_jobs, spatial_review, audit_log, packages, monitoring_dashboards, privacy}`; `useAnalytics()` `['operator','analytics']` → includes `spatial_cost {asks_today, today_usd, by_provider_usd, review, client_versions}`, `model_health`; `useCoverage()` `['operator','coverage']`.
- Mutations (all invalidate `['operator']` prefix): `reviewSpatial({id, action:'confirm'|'dismiss'})` → `PATCH /api/operator/spatial/{id}/review`; `setTrust({id, status:'verified'|'rejected'|'unverified'})` → `PATCH /api/operator/resources/{id}/trust {trust_status}`; `retryJob(id)` → `POST /api/operator/ingestion/{id}/retry`; `createPackage(body)` → `POST /api/operator/packages`; `uploadPackage(file)` → multipart `POST /api/operator/packages/upload`; `setPackageStatus({id,status})` → `PATCH /api/operator/packages/{id}/status {status}`; `createDashboard({name})` → `POST /api/operator/monitoring-dashboards`; `enroll({id, student_id})` → `POST /api/operator/monitoring-dashboards/{id}/students {student_id}`.

- [ ] **Step 1: Failing tests** — SpatialPage: snapshot with one pending item; clicking "Confirm" PATCHes `/api/operator/spatial/s1/review` with `{action:'confirm'}`. ResourcesPage: clicking "Verify" PATCHes trust; clicking "Retry" POSTs retry.
- [ ] **Step 3: Implement** — Overview: `Stat` grid from overview counts + readiness list. Users: table (name, role `Tag`, created) + goals table + audit log table. Resources: table with trust `Tag` + Verify/Reject/Reset buttons; ingestion jobs table with Retry on `failed`. Spatial: pending items (question preview, page title, confidence mono, ms) + Confirm/Dismiss; cost strip (`asks_today`, `$today`, per-provider) from analytics. Packages: table (slug, title, version, status `Tag`, publish/archive buttons), "New package" modal (slug, title, version, manifest JSON textarea), upload input. Analytics: `Stat`s for mastery buckets, model p50/p95/fallback, spatial cost, client versions table; coverage gaps table. Monitoring: create dashboard form, dashboards table (name, code mono), enroll form.
- [ ] **Step 4: Tests pass → commit** `feat(web): operator panel`

---

### Task 14: Amplify config, deploy wiring, extension detect domain, docs, old shell removal

**Files:**
- Create: `apps/web/amplify.yml`, `docs/WEB_APP.md`
- Modify: `scripts/deploy_aws.ps1` (add `[string]$WebOrigin = ""` param; add `WEB_ORIGINS = $(if ($WebOrigin) { "$WebOrigin,http://localhost:5173" } else { "http://localhost:5173" })` to `$envVars`), `scripts/package_extension.py` (`--dashboard-url` overrides `dashboardUrl` independently of `--api-base`), `apps/extension/manifest.json` (`content_scripts[0].matches` += `"https://*.amplifyapp.com/*"`), `README.md` (web app section), `Makefile` (`build-web` exists; add `web` = `cd apps/web && npm run dev`)
- Delete: `services/api/app/static/index.html`, `app.js`, `styles.css` (keep `point-and-ask/`); update `main.py` static mount so `/` no longer serves the old shell — mount `StaticFiles(directory=static_dir, html=True)` stays (landing lives at `/point-and-ask/`); add `@app.get("/")` returning a redirect to `settings.web_app_url` when set, else JSON `{"message": "StudyOS API", "web": "run apps/web"}`. Add `web_app_url: str | None = None` to Settings and `WEB_APP_URL` to `deploy_aws.ps1` env when `-WebOrigin` given.
- Test: `services/api/tests/test_platform.py` — if any test fetched `/` expecting HTML, update to expect the JSON/redirect; run full suites.

- [ ] **Step 1: amplify.yml**

```yaml
version: 1
applications:
  - appRoot: apps/web
    frontend:
      phases:
        preBuild:
          commands:
            - nvm use 20
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: dist
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
```

Amplify console settings (documented in `docs/WEB_APP.md`): rewrite `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>` → `/index.html` (200); env var `VITE_API_BASE=https://<app-runner-url>`.

- [ ] **Step 2: Sync check + tests**

Run: `py -3.12 scripts/sync_spatial.py` (manifest is not synced; edit `D:/PROJECTS/Spatial/extension/manifest.json` is not needed — standalone has no dashboard), `py -3.12 scripts/sync_spatial.py --check`, `cd services/api && py -3.12 -m pytest -q`, `cd apps/web && npm test && npm run build`.

- [ ] **Step 3: E2E smoke with the browser-automation skill**

Start API (`services/api`, `.env` present) and `npm run preview` in `apps/web`; script: open `/register`, fill name/email/password, expect `/onboarding`; skip → goal → expect Today heading; sign out → `/login`. Then `POST /api/auth/bootstrap-operator` with `OPERATOR_BOOTSTRAP_TOKEN` env to create an operator, open `/operator/login`, sign in, expect "Overview". Save screenshots to the scratchpad and review them.

- [ ] **Step 4: docs/WEB_APP.md** — run locally (`ollama serve`, API, `npm run dev`), env vars, build, Amplify steps, operator bootstrap command, how the extension detects the dashboard.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(web): amplify config, deploy wiring, docs; remove legacy static shell"
```
