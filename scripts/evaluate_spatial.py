"""Replayable fast-path Spatial Context evaluation.

This evaluates structural geometry/anchor resolution only. Vision/OCR evaluators
should use the same result contract when those providers are enabled.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).parents[1] / "services" / "api"))
from app.core.providers import resolve_spatial_marks


CASES = [
    ({"type": "rectangle", "x": 20, "y": 20, "width": 30, "height": 20}, True),
    ({"type": "point", "x": 40, "y": 40}, True),
    ({"type": "rectangle", "x": "bad", "y": 4, "width": 10, "height": 10}, False),
]


def main() -> int:
    latencies = []
    matched = 0
    for mark, should_match in CASES:
        started = perf_counter()
        result = resolve_spatial_marks([mark], {"width": 100, "height": 100},
                                       [{"id": "anchor-1", "type": "equation", "bbox": {"x": 10, "y": 10, "width": 60, "height": 60}}])
        latencies.append((perf_counter() - started) * 1000)
        actual_match = bool(result["candidates"] and result["candidates"][0].get("anchor_id"))
        matched += actual_match == should_match
    summary = {"cases": len(CASES), "anchor_expectation_accuracy": round(matched / len(CASES), 3),
               "p95_latency_ms": round(sorted(latencies)[min(len(latencies) - 1, int((len(latencies) - 1) * .95))], 3),
               "max_latency_ms": round(max(latencies), 3), "thresholds": {"accuracy": 1.0, "p95_latency_ms": 16}}
    print(json.dumps(summary, indent=2))
    return 0 if summary["anchor_expectation_accuracy"] >= 1 and summary["p95_latency_ms"] <= 16 else 1


if __name__ == "__main__":
    raise SystemExit(main())
