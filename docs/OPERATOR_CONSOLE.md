# StudyOS operator console

The operator surface is a quality-control and curriculum-studio boundary, not a private-content browser.

## Current controls

- `GET /api/operator/overview`: aggregate counts, readiness, and configured routes.
- `GET /api/operator/snapshot`: users, goals, resource metadata, ingestion jobs, low-confidence Spatial Context records, and audit events.
- `GET /api/operator/analytics`: mastery buckets, assessment/review signals, ingestion quality, Spatial Context latency/corrections, and model p50/p95/fallback telemetry.
- `GET /api/operator/coverage`: aggregate objective coverage and content-gap counts across the evidence graph.
- Session execution metrics are included in `/api/operator/overview` and `/api/operator/analytics`; the student Today surface can start and complete planned sessions.
- `PATCH /api/operator/resources/{id}/trust`: verify, reject, or return a resource to unverified status.
- `POST /api/operator/ingestion/{job_id}/retry`: retry a failed or retry-pending ingestion job.
- `POST /api/operator/goals/{goal_id}/phases`: add a curated phase.
- `POST /api/operator/phases/{phase_id}/topics`: add a curated topic.
- `PATCH /api/operator/topics/{topic_id}`: edit topic metadata with an audit record.
- `GET /api/operator/packages`: inspect draft/published/archived fixed packages.
- `POST /api/operator/packages` and `POST /api/operator/packages/upload`: author or upload a reviewed JSON/ZIP manifest; `PATCH /api/operator/packages/{id}/status` publishes it.
- `POST /api/operator/monitoring-dashboards`: create a leader-owned monitoring space; `POST .../{id}/students` enrolls by StudyOS ID.

The dashboard intentionally shows resource status, trust state, and quality signals without returning private document text or raw screen pixels. Student-owned objects remain protected by ownership checks; operator actions are role-gated in production and audit logged.

Monitoring reports are intentionally aggregate at the group boundary: progress, mastery, session activity, tracked minutes, and on-track status. It does not expose student documents, tutor conversations, college IDs, or private coding-account credentials.

## Version 2 operator workbench

The next operator increment should add curriculum template publishing/versioning, cohort comparisons, replayable retrieval/tutor evaluations, cost budgets, correction-label review, and aggregate export. These should remain aggregate or explicitly approved support workflows.
