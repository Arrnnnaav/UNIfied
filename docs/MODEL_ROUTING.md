# Model and latency policy

The platform uses a tiered model strategy rather than one model for every request.

Every tutor and Spatial Context execution records task, provider, model, status, latency, and (where applicable) confidence in aggregate-safe `model_events` telemetry. Operator analytics exposes p50/p95 latency and fallback rates without storing prompts, answers, document text, or screen pixels.

| Work | Default route | Why |
|---|---|---|
| Spatial mark validation, crop geometry, classification, rerank | Local small model or deterministic code | Keeps interaction private and responsive |
| OCR and UI/document grounding | Local vision model when available; plugin/DOM/UIA metadata first | Pixels are a fallback, not the only signal |
| Embeddings | Local sentence-transformer when installed; deterministic hashing fallback in the runnable slice | Stable, cacheable, inexpensive, and available offline |
| Tutor answer, assessment generation, curriculum synthesis | Configured strong API model, with local fallback | More reasoning capacity and better explanations |
| Mastery and recommendation scoring | Deterministic application service | Explainable and reproducible |

## Spatial latency budget

1. Capture mark locally and render immediately.
2. Validate geometry locally in under 16 ms where possible.
3. Resolve against supplied DOM/UIA/PDF accessibility anchors before invoking a vision model.
4. Send only a crop or redacted frame when policy permits.
5. Stream a provisional interpretation, then replace it with a verified resolution.

Spatial context is reference only. It never bypasses permissions, risk checks, approvals, or verification.

When the local route is Ollama, tutor requests use the native non-thinking transport with a bounded response and the student shell uses SSE (`/api/tutor/ask/stream`) so retrieval status is visible immediately while synthesis completes.

Retrieval uses a cached embedding route plus lexical overlap fallback. This keeps short notes answerable when an embedding model is cold or unavailable, while still requiring evidence thresholds before synthesis. Production startup schedules a bounded local-model warm-up and exposes its status through readiness telemetry; a configured OpenAI route can take over when local synthesis fails.

## Accuracy policy

Every grounded answer should carry:

- source locator(s),
- resolver/model provenance,
- confidence,
- whether evidence was sufficient,
- a fallback question when confidence is low.

The operator console should monitor disagreement, low-confidence resolutions, latency percentiles, model cost, and user corrections. Do not silently increase model size to hide poor grounding.
