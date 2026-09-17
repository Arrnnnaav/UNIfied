# spatial-core — golden cases for Spatial Context resolution

No build step, no shared runtime. The two authoritative implementations stay where they run:

- client: `apps/extension/geometry.js` (`strokeToMark`, `rankAnchors`)
- server: `services/api/app/core/providers.py` (`resolve_spatial_marks`)

`cases/*.json` are the contract: marks + anchors in, expected top anchor / ranking / polygon bbox out.
`test_resolver.py` runs every case through Python and (via `run_js.mjs`) through node and asserts both agree.

```powershell
py -3.12 -m pytest packages/spatial-core -q
```

Rules: every resolver bug fix adds a case first; scoring or tie-break changes must land on both sides in the
same commit; `expect` values are reviewed by a human, never regenerated from the implementation.
