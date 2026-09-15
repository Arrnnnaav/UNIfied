"""Replayable retrieval evaluation for short student questions and saved chunks."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "services" / "api"))
from app.core.providers import embed_text
from app.main import hybrid_chunk_score


@dataclass
class FakeChunk:
    text: str
    embedding_json: str = "[]"


CASES = [
    ("What does semantic retrieval use?", "Semantic retrieval uses embeddings to find related passages.", True),
    ("What is transaction isolation?", "A binary search uses an invariant over a sorted array.", False),
    ("How do HTTP responses work?", "An HTTP response contains a status code, headers, and an optional body.", True),
]


def main() -> int:
    outcomes = []
    for query, text, expected in CASES:
        chunk = FakeChunk(text)
        score = hybrid_chunk_score(query, embed_text(query), chunk)
        outcomes.append({"query": query, "expected": expected, "score": round(score, 3), "selected": score >= .22, "correct": (score >= .22) == expected})
    accuracy = sum(item["correct"] for item in outcomes) / len(outcomes)
    summary = {"cases": len(outcomes), "retrieval_accuracy": round(accuracy, 3), "threshold": .22, "outcomes": outcomes}
    print(json.dumps(summary, indent=2))
    return 0 if accuracy == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
