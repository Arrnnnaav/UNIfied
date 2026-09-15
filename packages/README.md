# Fixed StudyOS packages

The catalog is deterministic and operator-controlled. It is derived from Tracker's curated plan and can be reviewed, versioned, uploaded, published, and installed by students without asking an LLM to invent a curriculum.

Included starter packages:

- `rag-mastery.json` — foundations, advanced retrieval, agentic RAG, multimodal RAG, evaluation, and projects.
- `agent-foundations.json` — agent patterns, tool use, memory, and hands-on builds.
- `local-llm.json` — local inference, serving, quantization, privacy, and operations.
- `multimodal-rag.json` — vision-language foundations and applied multimodal retrieval.

Regenerate the manifests from the Tracker source plan with:

```powershell
py -3.12 scripts/build_package_catalog.py
```

An operator can upload any reviewed JSON manifest (or a ZIP containing `manifest.json`) from the operator console. Students see only published versions and can download/load them into a new goal.
