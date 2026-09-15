# Source-project reuse map

## Learning HQ (`tracker`)

Keep the product concepts and migrate the data deliberately:

| Existing capability | Unified destination |
|---|---|
| `arnav-learning-plan.json` | Goal → Phase → Topic seed/importer |
| `goals.json` and goal progress | Goal and learning-session services |
| link Inbox and priorities | Resource references and recommendation ranking |
| notes | Notes attached to resource/topic (not mastery evidence) |
| static Learning HQ UI | Interaction patterns only; StudyOS UI is the new shell |

The JSON files are valuable migration inputs, but must not remain the production source of truth.

## DocCluster (`textClust`)

Port behind an asynchronous ingestion boundary:

| Existing capability | Unified destination |
|---|---|
| PDF/DOCX/TXT parsers | `ParsedDocument` worker contract |
| chunker | `ResourceChunk` creation job |
| sentence-transformers embedder | embedding worker + pgvector |
| BM25 + cosine search | unified `/api/search` retrieval service |
| UMAP/HDBSCAN/BERTopic | optional semantic-map job |
| WebSocket pipeline events | ingestion-job progress events |

The student should be able to use the roadmap before semantic processing finishes; expensive ML belongs in workers.

## Current boundary

The MVP includes the domain entities and UI flow needed to prove the first vertical slice. It uses a portable SQLite development database and a lightweight substring search. This is deliberate: it keeps the product demonstrable while leaving the production persistence and ML jobs replaceable behind clear seams.
