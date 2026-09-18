# StudyOS — Unified Learning Platform

StudyOS is the student-first unified product described in `docs/MASTER_ARCHITECTURE.md`, with a runnable API, worker, student shell, and operator console.

It combines the strongest ideas from the two source projects:

- Learning HQ: goals, phases, roadmap, resources, priorities, notes, and progress.
- DocCluster: normalized resource content, parsing/search direction, semantic discovery, and knowledge-map direction.
- Spatial Context: a core `Point & Ask` interaction where a student circles an equation, diagram, paragraph, or code region on any web page or PDF (browser extension in `apps/extension`) and asks about exactly that.

## Run locally

From `learning-platform/services/api`:

```powershell
py -3.12 -m uvicorn app.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000>.

The primary student/operator UI is the React app in `apps/web` ("candlelit ink" design system):

```powershell
cd apps/web; npm ci; npm run dev   # http://localhost:5173 — proxies /api to :8000
```

See `docs/WEB_APP.md` for structure, tests, and the Amplify deployment path.

The default development database is SQLite so isolated tests and a quick local demo work without Docker. The included Compose stack is the production-shaped path for PostgreSQL/pgvector, Redis, MinIO, migrations, the API, worker, and static student/operator shell; it has been smoke-tested live in production mode with a local Ollama tutor route.

For production Compose, copy `.env.example` to `.env`, replace the JWT secret, and configure `LOCAL_LLM_BASE_URL`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`. Compose forwards these settings to the API; production intentionally refuses placeholder authentication or an unconfigured tutor route.

Provision the first operator with `POST /api/auth/bootstrap-operator` and the one-time `X-Operator-Bootstrap-Token` deployment secret, then rotate/remove that secret.

## Included vertical slice

- Today dashboard with next-best action and mastery stats
- Goal creation
- Phase/topic roadmap
- Custom topics
- Progress separate from mastery
- Resource and note capture
- Resource search endpoint with cached local/Ollama embeddings and deterministic offline fallback
- Grounded tutor with evidence locators and provider metadata
- Assessments, mastery evidence, review scheduling, and recommendations
- Persistent adaptive learning sessions: Today materializes planned work, start/complete actions create evidence, and session minutes feed progress and operator metrics
- Async ingestion worker with Redis and MinIO/S3 support
- Public GitHub README ingestion and feature-flagged YouTube transcript ingestion
- Point & Ask anywhere: Chrome extension overlay (freehand/circle/box), bundled pdf.js viewer for PDFs, DOM/PDF text anchors, optional crop, `/api/spatial-context/ask` with follow-up turns
- Persisted spatial marks with ownership checks
- Spatial correction feedback and operator quality telemetry
- Observed model runtime telemetry: provider/model, p50/p95 latency, fallback rate, and failures
- Authenticated student data export
- Confirmation-gated student account deletion
- Student onboarding with generated StudyOS ID, college/year/branch context, college ID, and optional LeetCode/GitHub links
- Fixed operator-curated package catalog with JSON/ZIP upload, publishing, download, and one-click student installation
- Operator-provisioned monitoring dashboards with enrolled-student aggregate progress, mastery, activity, minutes, and on-track signals
- Evidence-based milestones, badge titles, and StudyOS-ID milestone sharing
- Responsive student UI with Point & Ask history (marks made anywhere, carried into the tutor) and operator operations tables

## Production deployment notes

The core product path is working end to end. For a real student beta, finish deployment-specific hardening:

1. Configure a warm GPU-backed local tutor/vision runtime, or explicitly configure a hosted streaming provider when the stricter two-second synthesis target is required.
2. Enable and validate YouTube captions in deployments that need video learning; GitHub README ingestion is already connected.
3. Expand operator RBAC beyond the current student/operator boundary and add aggregate analytics export.
4. Configure backups, secret rotation, rate limits, TLS, and observability for the chosen hosting environment.

See `docs/REUSE_MAP.md` for the migration boundary and `docs/SPATIAL_CONTEXT.md` for the design decision.
See `docs/FUTURE_VERSION.md` for the production model-routing, latency, and accuracy contract.
