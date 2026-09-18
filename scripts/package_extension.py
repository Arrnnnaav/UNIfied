"""Zip the extension for the Chrome Web Store (or for sharing an unpacked build).

    py -3.12 scripts/package_extension.py                 # StudyOS build  -> dist/point-and-ask-<version>.zip
    py -3.12 scripts/package_extension.py --spatial       # standalone build from D:/PROJECTS/Spatial/extension
    py -3.12 scripts/package_extension.py --api-base https://xyz.awsapprunner.com   # bake the production API into config.js
Excludes dev/, tests/, README.md and anything the store does not need. Runs the geometry tests first.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"dev", "tests", "__pycache__"}
SKIP_FILES = {"README.md", ".DS_Store"}


def main() -> int:
    source = (
        Path(os.environ.get("SPATIAL_REPO", r"D:/PROJECTS/Spatial")) / "extension"
        if "--spatial" in sys.argv
        else ROOT / "apps/extension"
    )
    api_base = ""
    if "--api-base" in sys.argv:
        api_base = sys.argv[sys.argv.index("--api-base") + 1].rstrip("/")
    dashboard_url = ""
    if "--dashboard-url" in sys.argv:
        dashboard_url = sys.argv[sys.argv.index("--dashboard-url") + 1].rstrip("/") + "/"
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    tests = source / "tests/geometry.test.mjs"
    if tests.exists():
        subprocess.run(["node", "--test", str(tests)], check=True)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    slug = (
        manifest["name"]
        .lower()
        .replace("&", "and")
        .replace("\u2014", "")
        .replace("  ", " ")
        .strip()
        .replace(" ", "-")
    )
    out = dist / f"{slug}-{manifest['version']}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(source.rglob("*")):
            rel = path.relative_to(source)
            if path.is_dir() or rel.parts[0] in SKIP_DIRS or path.name in SKIP_FILES:
                continue
            if path.name == "config.js" and (api_base or dashboard_url):
                text = path.read_text(encoding="utf-8")
                if api_base:
                    text = re.sub(r"apiBase: '[^']*'", f"apiBase: '{api_base}'", text)
                text = re.sub(
                    r"dashboardUrl: '[^']*'",
                    f"dashboardUrl: '{dashboard_url or (api_base + '/')}'",
                    text,
                )
                bundle.writestr(str(rel).replace(os.sep, "/"), text)
                continue
            bundle.write(path, str(rel).replace(os.sep, "/"))
    size = out.stat().st_size / 1_048_576
    print(
        f"{out} ({size:.1f} MB) - upload at https://chrome.google.com/webstore/devconsole (Unlisted first)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
