# Point & Ask — deploy-ready pass for AWS "First Commit" (2026-09-18)

Solo, ~36 h. Pitch: Point & Ask (extension + cited answers) is the product; StudyOS is where marks live.
Track: "Deployed, with a URL" — App Runner (FastAPI container), Bedrock (provider), RDS Postgres or SQLite fallback, S3.

## Blockers
1. Bedrock provider (`kind: bedrock`, Converse API streaming, vision via image block) in Spatial `providers.py`; synced to StudyOS. Env: `AWS_REGION`, `BEDROCK_MODEL`, `BEDROCK_VISION_MODEL`; credentials from the App Runner instance role or env keys.
2. Container start runs `alembic upgrade head` then uvicorn (`docker/entrypoint.sh`); `apprunner.yaml`; `scripts/deploy_aws.ps1` (ECR push, App Runner create/update). SQLite path works when no RDS.
3. Burst limit: 10 asks / 60 s per actor (in-memory sliding window) on top of daily quota → 429 `RATE_LIMITED`.
4. Anonymous expiry: daily background task deletes `role=anonymous` users + contexts + usage older than 30 days; also runs at startup.
5. `package_extension.py --api-base URL` bakes prod API into `config.js` of the zip; popup override stays.
6. `/api/health` includes `db: ok|error` (SELECT 1); App Runner health check path `/api/health`.
7. `client_version` stored on `model_events` (spatial_answer) for operator analytics.

## Features
A. Explain level: `level: eli5|student|expert` on ask payload; panel segmented control; one system-prompt line per level; persisted in extension storage.
C. Diagram mode: when the mark has no text anchors and a crop is attached, force vision-first + OCR and tell the user ("no text under mark — reading the image"); footer shows `diagram`.

## Non-goals
Cognito, DynamoDB rewrite, Strands SDK, share pages, language auto-detect, new StudyOS shell features.

## Testing
pytest for 3, 4, 6, 7, A prompt selection, C detection; Bedrock provider unit test with a stubbed client; existing 16/29 suites stay green; sync check green; harness QA screenshot.
