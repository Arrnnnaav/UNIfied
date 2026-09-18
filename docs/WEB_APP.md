# StudyOS Web App (`apps/web`)

The student-facing React application. Replaces the legacy single-file shell
(`services/api/app/static/app.js`) once parity is verified.

Spec: `docs/superpowers/specs/2026-09-18-studyos-web-app-design.md`
Plan: `docs/superpowers/plans/2026-09-18-studyos-web-app.md`

## Stack

Vite 5 · React 18 · TypeScript · Tailwind 3 ("candlelit ink" tokens) · React Router 6 ·
TanStack Query 5 · Vitest + Testing Library. Node 20.

## Develop

```bash
cd apps/web
npm ci
npm run dev        # http://localhost:5173, proxies /api to :8000
```

Requires the API running on port 8000 (`cd services/api && uvicorn app.main:app --port 8000`).
`VITE_API_BASE` overrides the API origin when the proxy is not used.

## Test

```bash
npm test           # vitest: client, sse, guards, auth, onboarding, today, ...
npx tsc --noEmit   # typecheck (build gate)
```

## Build

```bash
npm run build      # dist/ — what Amplify serves
```

## Deploy (AWS Amplify Hosting)

1. Create an Amplify app connected to this repo. The build spec is `apps/web/amplify.yml`
   (`appRoot: apps/web`, Node 20, `npm ci && npm run build`, SPA rewrite to `/index.html`).
2. Set environment variable `VITE_API_BASE=https://<app-runner-url>`.
3. Point the API at the Amplify origin so CORS accepts it:

   ```powershell
   .\scripts\deploy_aws.ps1 -Region us-east-1 -WebOrigin https://main.<app-id>.amplifyapp.com
   ```

   This sets `WEB_ORIGINS=<web>,http://localhost:5173` and `WEB_APP_URL=<web>` (so the API root
   `/` redirects to the React app).

4. Ship the extension with the hosted dashboard baked in:

   ```powershell
   py -3.12 scripts\package_extension.py --api-base https://<app-runner-url> --dashboard-url https://main.<app-id>.amplifyapp.com
   ```

   The extension's `detect.js` content script already matches `https://*.amplifyapp.com/*`, so the
   Point & Ask card on the hosted app shows "Extension installed (v…)".

## Structure

```
src/api/      client.ts (fetch + ApiError + 401 handling), sse.ts (readSse), types.ts
src/auth/     AuthProvider (me query, refresh, signOut), guards.tsx, storage.ts
src/components/  Button Card Stat Tag Field Select Table EmptyState Toast Modal Spinner PageHeader
src/layouts/  AppLayout (student sidebar), OperatorLayout (operator topbar + tabs)
src/features/ one directory per route: auth, onboarding, today, roadmap, resources,
              tutor, pointask, milestones, monitoring, profile, operator
auth/token → localStorage.studyos_token; device id → localStorage.studyos_device
```

## Rules

- TanStack Query owns server state; no global store beyond `AuthProvider`.
- Loading → `Spinner`, empty → `EmptyState` with the one action that fills it, errors → inline or `Toast`.
- 401s redirect to `/login` via the client's unauthorized handler; operator routes guard on `role === 'operator'`.
- Design tokens live in `tailwind.config.ts`; no new colors outside the token set.
