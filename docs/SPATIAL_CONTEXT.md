# Spatial Context / Point & Ask

Spatial Context is a core context primitive, not a student-only agent and not a plugin.

The MVP stores:

```text
goal_id
utterance
marks[]
source
timestamp
```

The browser canvas currently emits rectangle marks. The production representation should support circles, polygons, points, arrows, full-frame/crop references, active application or document, candidate UI/DOM/accessibility objects, confidence, and sensitivity policy.

For students, the interaction is especially strong for equations, charts, anatomy diagrams, circuit diagrams, PDFs, and code. The mark reduces the burden of describing exactly what confused them, and the utterance preserves the learning intent.

The safety invariant is important: a mark establishes reference, never authority. Any future tutor action or computer action still needs normal permission, risk, approval, execution, and verification checks.

Privacy should default to local or redacted context. Prefer document structure, PDF coordinates, DOM, or accessibility metadata over sending an entire screen. Only send a crop/full frame when policy allows it.
