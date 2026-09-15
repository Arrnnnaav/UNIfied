# Database migrations

The application currently has a development-only `create_all` bootstrap and a SQLite compatibility bridge so the vertical slice starts without infrastructure. Production deployment must replace that bootstrap with Alembic migrations before enabling multi-worker API instances.

The migration sequence from the master architecture is:

```text
001_users_auth
002_learner_profiles
003_goals
004_curricula_phases_topics
005_objectives_dependencies
006_resources_documents_chunks
007_embeddings_alignment
008_assessments_mastery
009_gaps_recommendations_reviews
010_operator_analytics_audit
```

Do not run schema mutation from request handlers. The current SQLite bridge exists only for local development and is intentionally documented as temporary.
