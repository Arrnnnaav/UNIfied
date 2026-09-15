# StudyOS future production version

## Version 2 release shape

The next production version should preserve the current vertical slice and add capability in this order:

1. **Warm intelligence runtime:** GPU-backed Ollama or an explicitly selected hosted streaming model, model health probes, warm-up status, bounded token budgets, and automatic cloud fallback only when configured.
2. **Evidence graph:** objective-level coverage, semantic concepts, prerequisite edges, source freshness, and conflict detection. Coverage must remain separate from completion and mastery.
3. **Precision Spatial Context:** browser/DOM accessibility adapters, PDF coordinate adapters, OCR, crop redaction, multi-mark grouping, overlap-ranked anchors, calibrated confidence, and correction replay evaluation.
4. **Adaptive study planner:** daily sessions, deadline-aware workload, spaced review, practice generation, and explainable next-best-action recommendations.
5. **Operator quality loop:** cohort-level dashboards, prompt/model version comparisons, replay datasets, cost budgets, trust workflows, correction queues, and exportable aggregate reports.

The current release already provides the production-shaped foundation for these additions: Postgres/pgvector, Redis workers, S3-compatible storage, routed local tutor synthesis, structured Spatial Context, SSE delivery, privacy-bounded operator telemetry, persistent semantic concepts, topic alignment, explicit prerequisites, adaptive Today planning, persistent learning sessions with evidence, GitHub ingestion, and feature-flagged YouTube transcript ingestion.

StudyOS should use a routed intelligence stack, not one oversized model for every interaction.

## Runtime tiers

1. **Interaction tier (local, always-on):** deterministic geometry validation, UIA/DOM/PDF structure, OCR, and a small local vision encoder. It targets sub-100 ms mark feedback and never uploads raw screen pixels by default.
2. **Retrieval tier (local):** a cached sentence-transformer embedder, BM25, pgvector, reranking, and document-level deduplication. Retrieval must finish before tutor synthesis and must expose its source locators.
3. **Reasoning tier (routed):** a local OpenAI-compatible model for private/offline work, with OpenAI or Anthropic as an explicitly configured stronger synthesis route. Every answer is grounded in retrieved evidence and reports provider/model status.
4. **Evaluation tier (operator-controlled):** replayable tutor, retrieval, and Spatial Context cases with acceptance thresholds for grounding, confidence calibration, latency, and correction rate.

## Spatial Context accuracy loop

The fast path is: capture locally → normalize geometry → resolve against DOM/UIA/PDF structure → use OCR → use a local vision model only when structure is unavailable → ask for confirmation when confidence is low. Student corrections are stored as labeled feedback and are never silently overwritten.

Target budgets:

- geometry validation: under 16 ms;
- structural resolution: under 100 ms;
- local OCR/vision fallback: under 500 ms when warm;
- tutor first response: under 2 seconds with a warm local model or streamed cloud response.

The current student shell uses streamed tutor delivery; on CPU-only local inference, final synthesis is slower than this target, so production deployments should use a GPU-backed local runtime or a hosted streaming provider when the stricter budget is required.

The operator console should show p50/p95 latency, low-confidence rate, correction rate, retrieval evidence sufficiency, ingestion failure rate, model fallback rate, and cost. It must show aggregate quality signals only—not private text or raw screen captures.

## Version 2.1 — Student network and institutional delivery

The next release adds a controlled distribution layer around the learning loop:

- student accounts carry a generated StudyOS ID plus private college, year, branch, and college-ID context; optional LeetCode/GitHub handles are learner-controlled profile links;
- fixed, versioned package manifests are authored and uploaded by the operator, published after review, and installed by students as normal goals with phases, objectives, resources, and evidence-based milestones;
- monitoring dashboards are provisioned only by the operator, assigned to a leader, and limited to enrolled-student aggregates: progress, mastery, activity, tracked minutes, and on-track status;
- milestone shares address a recipient's StudyOS ID and expose only the selected milestone, badge title, and message—never private documents, tutor conversations, or raw analytics.

The package system is intentionally separate from per-student AI generation. LLMs can personalize tutoring and Point & Ask, while the curriculum contract remains stable, reviewable, reproducible, and identical across a cohort.

## Production gates

- Postgres/pgvector migration completes before API readiness.
- Redis queue and shared object storage are healthy before asynchronous ingestion is enabled.
- Production Compose forwards and validates JWT and LLM provider configuration; development may use the offline fallback for local smoke tests.
- Model warm-up is explicit and observable; no request may trigger an unbounded model download.
- A tutor answer without sufficient evidence must say that evidence is insufficient.
- A Spatial Context interpretation below the confidence threshold must request confirmation before grounding a high-impact action.
- Student export and deletion/retention workflows remain available independently of operator access; the current deletion path is explicit and confirmation-gated.
