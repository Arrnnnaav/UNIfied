# StudyOS web app (React) — login, onboarding, student shell, separate operator panel

Date: 2026-09-18. Replaces the single-file `services/api/app/static/app.js` shell with a React app in
`apps/web`, hosted on AWS Amplify Hosting, talking to the existing FastAPI API. Visual system copied from
`D:/unified/tracker/frontend/public/style.css` ("candlelit ink").

## Goals

1. Real login/register/sign-out; no demo auto-login in the web app.
2. Onboarding wizard for new accounts (profile, first goal).
3. Operator panel on its own route tree with its own login gate, invisible to students.
4. Every existing student surface rebuilt: Today, Roadmap, Resources, Tutor, Point & Ask, Milestones,
   Monitoring, Profile.
5. Design pass: one token set, one component kit, consistent typography.

Non-goals: new backend features beyond the two endpoints below; charts; dark/light toggle (dark only);
mobile-first layouts (must not break at phone width, but desktop is the target); i18n.

## Stack

Vite 5, React 18, TypeScript, Tailwind 3 (theme = tracker tokens), React Router 6, TanStack Query 5,
Vitest + Testing Library. Node 20. Package root `apps/web`. No UI library.

Design tokens (Tailwind `theme.extend.colors` + fonts):

```
bg #16120d  surface #1e1811  surface2 #292116  surface3 #382c1c
accent #8fb89a  accent-tint #22301f  accent-strong #b8dcc0
accent2 #d7929c  accent2-tint #3a2228          (dusty rose = "now/active")
text #f1e7d6  text-dim #c2b39c  text-muted #8a7c66
ok #8fb89a  yellow #e0b969  red #e08a8a
border rgba(241,231,214,.10)  border-strong rgba(241,231,214,.20)
radius 4px  shadow 0 10px 26px rgba(0,0,0,.4)
display: Fraunces (Google Fonts)  body: Work Sans  mono: IBM Plex Mono
```

Paper-grain `body::before` overlay and 2 px solid `text`-colour rules on top bars, as in tracker.
Point & Ask keeps pink `#ff3d7f` only for the mark stroke in screenshots; in the web app its accent is
`accent2`.

## Backend changes (small)

- `WEB_ORIGINS` setting (comma list) appended to CORS `allow_origins`; default includes
  `http://localhost:5173`.
- `GET /api/auth/me` → `{id, name, email, role, student_id, has_goals: bool, profile_complete: bool}`.
  `profile_complete` = learner profile has `education_stage != "other"` or any of college fields set.
- `apps/extension/manifest.json` + `config.js`: `detect.js` also matches `https://*.amplifyapp.com/*`;
  `dashboardUrl` baked by `package_extension.py --dashboard-url`.
- `services/api/app/static/` keeps the landing (`/point-and-ask/`) and privacy page; the old shell
  (`index.html`, `app.js`, `styles.css`) is deleted once the React app reaches parity (last task of the plan).

## App structure

```
apps/web/
  index.html  vite.config.ts  tailwind.config.ts  tsconfig.json  amplify.yml  package.json
  src/main.tsx  src/App.tsx (router)  src/styles.css (tokens, grain, fonts)
  src/api/client.ts        fetch wrapper: base URL, bearer, JSON errors {code,message}, 401 -> /login
  src/api/sse.ts           readSse(fetch Response body, onEvent, AbortSignal) shared by Tutor + Point & Ask; aborted on unmount
  src/api/types.ts         response types for the endpoints used
  src/auth/                AuthProvider (me query), useAuth(), RequireStudent, RequireOperator, storage
  src/components/          Card Stat Tag Button Field Select Table EmptyState Toast Modal Spinner PageHeader
  src/layouts/AppLayout    sidebar nav (student), topbar with user + sign-out
  src/layouts/OperatorLayout  topbar "OPERATOR", side tabs, no student nav
  src/features/<name>/     page + hooks + small components per route
  src/test/                setup, msw-free fetch mocks, helpers
```

## Routes

| Path | Guard | Page |
|---|---|---|
| `/login`, `/register` | none (redirect to `/` when signed in) | Auth pages |
| `/onboarding` | student; skipped when `has_goals` | Wizard |
| `/` | student, `has_goals` else `/onboarding` | Today |
| `/roadmap` | student | Roadmap |
| `/resources` | student | Resources |
| `/tutor` | student | Tutor |
| `/point-and-ask` | student | Point & Ask |
| `/milestones` | student | Milestones |
| `/monitoring` | student | Monitoring (join by code, my dashboards) |
| `/profile` | student | Profile |
| `/operator/login` | none | Operator login |
| `/operator` | role=operator | Overview |
| `/operator/users` `/resources` `/spatial` `/packages` `/analytics` `/monitoring` | role=operator | Operator pages |
| `*` | — | 404 |

Roles in the backend are exactly `student | operator | anonymous`. Guards: `RequireStudent` = token present and
`/api/auth/me` ok (any role). `RequireOperator` = role == `operator`; other roles see "This account is not an operator" with sign-out. Student sidebar never links
to `/operator`. Sign-out = clear token + query cache → `/login`.

## Pages and the endpoints they use

- **Login/Register**: `POST /api/auth/login`, `POST /api/auth/register` (name, email, password;
  college fields moved to onboarding). Errors shown inline. Register → `/onboarding`.
- **Onboarding**: step 1 `PATCH /api/me/profile` (education_stage, college_name, college_year, branch,
  current_skill_level, learning_modes, preferred_pace); step 2 `POST /api/goals` (title, goal_type,
  weekly_hours, target_date) → invalidate `me` → `/`. "Skip" on step 1 jumps to step 2; step 2 cannot be skipped
  (Today requires a goal).
- **Today**: `GET /api/dashboard` (stats, today, sessions, spatial_reviews, plan_status),
  `GET /api/recommendations`, `POST/PATCH /api/learning-sessions`, `POST /api/review/{id}/complete`.
- **Roadmap**: goal from dashboard; `PATCH /api/topics/{id}/progress`, `POST /api/topics`,
  `POST /api/topics/{id}/assessment` + `POST /api/assessments/{id}/attempt`, `GET /api/goals/{id}/coverage`.
- **Resources**: `POST /api/resources`, `POST /api/resources/upload`, `.../ingest-url|github|youtube`,
  `GET /api/ingestion/jobs`, `GET /api/search`.
- **Tutor**: `POST /api/tutor/ask/stream` (SSE), optional `spatial_context_id` from Point & Ask.
- **Point & Ask**: `GET /api/spatial-context`, `POST /api/spatial-context/{id}/quiz`, extension
  detection via `document.documentElement.dataset.pointAskExtension`, install card otherwise.
- **Milestones**: `GET/POST /api/milestones`, `POST /api/milestones/{id}/share`, `GET /api/milestone-shares`.
- **Monitoring** (student): `GET /api/monitoring-dashboards`, `GET .../{id}`, `POST /api/monitoring/join/{code}`.
- **Profile**: `GET/PATCH /api/me/profile`, `GET /api/me/export` (download), `DELETE /api/me` (confirm modal).
- **Operator overview**: `GET /api/operator/overview`.
- **Operator users**: `GET /api/operator/snapshot` (users, goals, audit_log).
- **Operator resources**: snapshot resources + ingestion_jobs; `PATCH .../resources/{id}/trust`,
  `POST .../ingestion/{id}/retry`.
- **Operator spatial**: snapshot `spatial_review`; `PATCH .../spatial/{id}/review`.
- **Operator packages**: `GET/POST /api/operator/packages`, `POST .../packages/upload`, `PATCH .../status`.
- **Operator analytics**: `GET /api/operator/analytics`, `GET /api/operator/coverage` (stat tiles + tables).
- **Operator monitoring**: `POST /api/operator/monitoring-dashboards`, `POST .../{id}/students`.

Loading = skeleton rows; errors = inline `Toast` with the API `message`; empty = `EmptyState` with the
one action that fills it.

## Data & state

TanStack Query for all reads with array keys (`['me']`, `['dashboard']`, `['goals', id, 'coverage']`,
`['spatial']`, `['operator', 'snapshot']`); mutations invalidate by prefix. Auth token in
`localStorage.studyos_token`. The web app never sends `X-Device-ID`: it always requires sign-in;
anonymous Point & Ask history lives in the extension and is adopted server-side at login. No global
store beyond `AuthProvider`.

## Error handling

`client.ts` normalises FastAPI errors: `detail` string → `{code:"ERROR", message}`, `detail` object →
as-is. 401 anywhere → clear token, redirect `/login?next=…`. 403 on operator routes → "not an operator"
screen. Network failure → Toast "API unreachable at <base>".

## Testing

- Vitest: `client.ts` (bearer header, 401 redirect, error normalisation), `sse.ts` (event parsing),
  guards (student/operator/onboarding redirects), onboarding wizard flow, one render test per page with
  mocked fetch (page shows data from fixture).
- E2E smoke (browser-automation skill, local API + `vite preview`): register → onboarding → Today →
  sign-out → operator login with bootstrapped operator → `/operator/spatial` confirm action.
- `make build-web` = `npm ci && npm run build` in `apps/web`; must pass typecheck.

## Deployment

Amplify Hosting, app root `apps/web`, build via `apps/web/amplify.yml` (node 20, `npm ci`, `npm run
build`, artifacts `dist`), rewrite `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>`
→ `/index.html` 200. Env `VITE_API_BASE=https://<app-runner-url>`. API `WEB_ORIGINS` set to the Amplify
domain in `deploy_aws.ps1` (new `-WebOrigin` param). Local dev: `npm run dev` with proxy `/api` → 8000.

## Task order

1. Backend: `/api/auth/me`, `WEB_ORIGINS` (with tests).
2. Scaffold, tokens, fonts, component kit, layouts, router with placeholders; `client.ts`, `sse.ts`,
   AuthProvider, guards, Login/Register.
3. Onboarding wizard.
4. Today, Roadmap, Resources.
5. Tutor, Point & Ask (extension detect, quiz later).
6. Milestones, Monitoring, Profile.
7. Operator layout + login + all operator pages.
8. Tests, e2e smoke, Amplify config, deploy script param, extension detect domain, delete old shell, docs.
