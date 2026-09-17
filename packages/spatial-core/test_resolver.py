"""Golden cases for Spatial Context resolution, run against BOTH implementations:
- services/api/app/core/providers.py::resolve_spatial_marks (server)
- apps/extension/geometry.js::rankAnchors / strokeToMark (client, via node)

    py -3.12 -m pytest packages/spatial-core -q       # from learning-platform/
Add a case for every resolver bug fix; both sides must agree on top anchor, ranking and polygon bbox.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "services" / "api"))
from app.core.providers import resolve_spatial_marks  # noqa: E402

CASES = sorted(ROOT.glob("cases/*.json"))
NODE = shutil.which("node")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def python_resolution(case: dict) -> list[dict]:
    resolution = resolve_spatial_marks(case["marks"], case["canvas"], case["anchors"])
    out = []
    for mark, candidate in zip(resolution["normalized_marks"], resolution["candidates"]):
        out.append({"role": candidate["role"], "bbox": {k: mark.get(k, 0) for k in ("x", "y", "width", "height")},
                    "top": candidate.get("anchor_id"), "ranked": [item["id"] for item in candidate.get("anchors_ranked", [])]})
    return out


def js_resolution(case_path: Path) -> list[dict]:
    result = subprocess.run([NODE, str(ROOT / "run_js.mjs"), str(case_path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)["marks"]


@pytest.mark.parametrize("case_path", CASES, ids=[p.stem for p in CASES])
def test_python_matches_expectation(case_path: Path):
    case = load(case_path); expect = case["expect"]; marks = python_resolution(case)
    if "tops" in expect:
        assert [m["top"] for m in marks] == expect["tops"]
        assert [m["role"] for m in marks] == expect["roles"]
    else:
        assert marks[0]["top"] == expect["top"]
        assert marks[0]["ranked"] == expect["ranked"]
    if "bbox" in expect:
        assert marks[0]["bbox"] == expect["bbox"]


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize("case_path", CASES, ids=[p.stem for p in CASES])
def test_js_matches_python(case_path: Path):
    case = load(case_path)
    py = python_resolution(case); js = js_resolution(case_path)
    assert len(py) == len(js)
    for p, j in zip(py, js):
        assert j["top"] == p["top"], f"top anchor differs: js={j['top']} py={p['top']}"
        assert j["ranked"] == p["ranked"], f"ranking differs: js={j['ranked']} py={p['ranked']}"
        assert {k: round(float(v), 2) for k, v in j["bbox"].items()} == {k: round(float(v), 2) for k, v in p["bbox"].items()}
