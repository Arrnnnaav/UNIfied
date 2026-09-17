# StudyOS acceptance matrix

| Capability | Evidence |
|---|---|
| Student authentication and ownership | `services/api/tests/test_platform.py` |
| Student identity and college onboarding | `services/api/tests/test_community_features.py`, `/api/auth/register`, `/api/me/profile` |
| Fixed package catalog and installation | `services/api/tests/test_community_features.py`, `/api/packages`, `/api/operator/packages` |
| Operator-provisioned monitoring dashboards | `services/api/tests/test_community_features.py`, `/api/operator/monitoring-dashboards` |
| Milestone titles and student-ID sharing | `services/api/tests/test_community_features.py`, `/api/milestones/{id}/share` |
| Learner profile onboarding and export | `/api/me/profile`, migration `0004_learner_profiles`, platform test |
| Goals, phases, topics, progress and mastery | `services/api/app/main.py` dashboard/roadmap endpoints |
| Deadline-aware adaptive Today status | `/api/dashboard` returns ranked actions plus explainable plan status |
| Explicit curriculum prerequisites | migration `0005_topic_dependencies`, `/api/topics/{topic_id}/dependencies`, recommendation/map edges |
| Learning HQ import | `/api/import/learning-hq` |
| File and note ingestion | `services/worker/tests/test_worker.py`, learning-loop acceptance test |
| URL ingestion and retry | API/worker ingestion paths with audited operator retry |
| GitHub README ingestion | `/api/resources/{resource_id}/ingest-github`, bounded public GitHub API adapter, async worker path |
| Grounded tutor with citations | `services/api/tests/test_learning_loop.py` |
| Replayable retrieval evaluation | `scripts/evaluate_retrieval.py` (3 cases, 100% deterministic retrieval accuracy) |
| Replayable tutor grounding/refusal evaluation | `scripts/evaluate_tutor.py` (grounded citation and unsupported-question refusal cases) |
| Low-lag tutor delivery | `/api/tutor/ask/stream` emits immediate status then grounded completion |
| Assessments, mastery evidence, reviews | learning-loop acceptance test |
| Persistent adaptive learning sessions | `services/api/tests/test_sessions.py`, `/api/learning-sessions` |
| Semantic search | `/api/search` and student Resources view |
| Hybrid objective coverage and operator content-gap aggregate | `/api/topics/{topic_id}/coverage`, `/api/goals/{goal_id}/coverage`, `/api/operator/coverage` |
| Persistent semantic concepts and topic alignment | migration `0006_semantic_alignment`, `/api/goals/{goal_id}/semantic-concepts` |
| Knowledge map | `/api/knowledge-map` and learning-loop acceptance test |
| Spatial Context normalization | spatial preview and correction tests |
| Point & Ask anywhere (extension) | `services/api/tests/test_spatial_ask.py` (`/api/spatial-context/ask`, follow-ups, ownership, stream), `apps/extension/tests/geometry.test.mjs`, dev harness `apps/extension/dev/harness.html` |
| Resolver parity client ↔ server | `packages/spatial-core/cases/*.json` via `pytest packages/spatial-core` (Python + node) |
| Spatial fast-path evaluation | `scripts/evaluate_spatial.py` (anchor expectation accuracy and p95 latency thresholds) |
| Student correction feedback | `/api/spatial-context/{id}/correct` |
| Operator privacy and quality telemetry | `/api/operator/snapshot`, `/api/operator/analytics` |
| Student data portability | `/api/me/export` |
| Student deletion and lifecycle control | Explicitly confirmed `/api/me?confirm=DELETE` |
| Secure URL redirects and upload boundaries | `web_ingestion.py`, upload size/name validation |
| Production readiness behavior | `/api/health/ready` returns 503 when production dependencies are unhealthy |
| Browser security baseline | global response security-header middleware |
| Retry/idempotency safety | worker content-hash deduplication and retry payload preservation |
| Code/configuration verification | 6 tests, Python compilation, JavaScript syntax, Compose config |
| Live container stack | Verified with PostgreSQL, Redis, MinIO, migrations, API, worker, UI, and async ingestion in the development profile; production mode additionally requires configured JWT and LLM credentials |
| Reproducible demo environment | `scripts/seed.py` creates an operator, two students, and representative goals/topics/resources |
