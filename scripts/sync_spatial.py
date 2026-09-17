"""Keep StudyOS and the standalone Spatial repo (D:/PROJECTS/Spatial) in sync.

Direction of truth:
  Spatial -> StudyOS : server/app/{providers,ocr,audio,research}.py  -> services/api/app/core/spatial/ (imports rewritten)
  StudyOS -> Spatial : apps/extension/* (except config.js) -> extension/
                       resolve_spatial_marks (providers.py) -> server/app/resolver.py
                       packages/spatial-core/cases/*.json   -> server/tests/cases/

    py -3.12 scripts/sync_spatial.py            # sync both ways
    py -3.12 scripts/sync_spatial.py --check    # exit 1 if anything is out of date (CI)
"""

from __future__ import annotations

import filecmp
import os
import re
import shutil
import sys
from pathlib import Path

STUDYOS = Path(__file__).resolve().parents[1]
SPATIAL = Path(os.environ.get("SPATIAL_REPO", r"D:/PROJECTS/Spatial"))

IMPORT_REWRITES = [
    (r"^from app\.config import", "from app.core.spatial.config import"),
    (r"^from app\.ocr import", "from app.core.spatial.ocr import"),
    (r"^from app\.audio import", "from app.core.spatial.audio import"),
    (r"^from app\.research import", "from app.core.spatial.research import"),
]
EXTENSION_SKIP = {"config.js", "manifest.json", "README.md", "dev", "tests", "vendor"}
VENDOR_FILES = ["pdf.min.mjs", "pdf.worker.min.mjs", "pdf_viewer.css", "LICENSE"]


def rewrite_imports(text: str) -> str:
    lines = []
    for line in text.splitlines(keepends=True):
        for pattern, replacement in IMPORT_REWRITES:
            line = re.sub(pattern, replacement, line)
        lines.append(line)
    return "".join(lines)


def extract_resolver() -> str:
    source = (STUDYOS / "services/api/app/core/providers.py").read_text(
        encoding="utf-8"
    )
    start = source.index("def resolve_spatial_marks(")
    body = source[start:]
    body = body.replace(
        'def resolve_spatial_marks(marks: list[dict], canvas: dict | None = None, anchors: list[dict] | None = None, image_data: str | None = None, utterance: str = "") -> dict:',
        "def resolve_marks(marks: list[dict], canvas: dict | None = None, anchors: list[dict] | None = None) -> dict:",
    )
    body = body.replace(
        "    vision = _resolve_local_vision(image_data, utterance, marks)\n", ""
    ).replace('            "vision": vision,\n', "")
    header = (
        '"""Deterministic mark resolver: normalizes marks, derives bounding boxes for freehand strokes,\n'
        "and ranks the DOM/PDF anchors under each mark. Runs before any model call and explains its confidence.\n"
        'SYNCED from StudyOS services/api/app/core/providers.py::resolve_spatial_marks by scripts/sync_spatial.py."""\n'
        "from __future__ import annotations\n\nfrom time import perf_counter\n\n\n"
    )
    return header + body


def plan() -> list[tuple[Path, Path, str | None]]:
    """(source, destination, transformed_text_or_None) for every synced file."""
    items: list[tuple[Path, Path, str | None]] = []
    for name in ("providers.py", "ocr.py", "audio.py", "research.py"):
        src = SPATIAL / "server/app" / name
        items.append(
            (
                src,
                STUDYOS / "services/api/app/core/spatial" / name,
                rewrite_imports(src.read_text(encoding="utf-8")),
            )
        )
    ext = STUDYOS / "apps/extension"
    for src in ext.iterdir():
        if src.name in EXTENSION_SKIP or src.is_dir():
            continue
        items.append((src, SPATIAL / "extension" / src.name, None))
    for name in VENDOR_FILES:
        items.append((ext / "vendor" / name, SPATIAL / "extension/vendor" / name, None))
    for src in (ext / "icons").glob("*.png"):
        items.append((src, SPATIAL / "extension/icons" / src.name, None))
    for src in (ext / "tests").glob("*.mjs"):
        items.append((src, SPATIAL / "extension/tests" / src.name, None))
    items.append(
        (
            STUDYOS / "services/api/app/core/providers.py",
            SPATIAL / "server/app/resolver.py",
            extract_resolver(),
        )
    )
    for src in (STUDYOS / "packages/spatial-core/cases").glob("*.json"):
        items.append((src, SPATIAL / "server/tests/cases" / src.name, None))
    return items


def main() -> int:
    check = "--check" in sys.argv
    stale = 0
    for src, dst, text in plan():
        if text is None:
            same = dst.exists() and filecmp.cmp(src, dst, shallow=False)
        else:
            same = dst.exists() and dst.read_text(encoding="utf-8") == text
        if same:
            continue
        stale += 1
        if check:
            print(f"out of date: {dst}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if text is None:
            shutil.copyfile(src, dst)
        else:
            dst.write_text(text, encoding="utf-8")
        print(
            f"synced {src.relative_to(src.parents[2]) if src.is_relative_to(STUDYOS) else src} -> {dst}"
        )
    if check:
        print("in sync" if not stale else f"{stale} file(s) out of date")
        return 1 if stale else 0
    print(f"{stale} file(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
