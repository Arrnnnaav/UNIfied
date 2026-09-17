# Spatial Context Anywhere — design

Date: 2026-09-15. Status: approved in chat, implementing.

## Problem

Point & Ask currently lives inside the StudyOS shell: the student must open the
Point & Ask view, optionally upload an image, and drag a rectangle on a blank
canvas. The reference interaction (HeyClicky "spatial context") is the
opposite: press a hotkey while reading *anything* in the browser, scribble a
circle over the confusing part, ask a question, get an answer about exactly
that region.

## Decision

Deliver Spatial Context as a Chrome (MV3) extension plus a bundled pdf.js
viewer, backed by a new `/api/spatial-context/ask` endpoint. The StudyOS
Point & Ask view becomes the history/replay surface for marks made anywhere.

Alternatives rejected: extension without PDF support (Chrome's built-in PDF
viewer blocks content scripts, so downloaded PDFs would not work); Electron
desktop overlay (system-wide but screenshot-only context, large build).

## Components

### 1. Extension — `apps/extension/`

- `manifest.json` MV3. Permissions: `activeTab`, `scripting`, `storage`,
  `tabs`, `webNavigation`, host `<all_urls>`. Command `Alt+Shift+A`.
- `background.js`: hotkey/toolbar click → inject `content.js` + `overlay.css`
  into the active tab and send `spatial:start`. Handles `spatial:capture`
  (`chrome.tabs.captureVisibleTab`, crops to mark bbox with `OffscreenCanvas`),
  `spatial:ask` (POST to StudyOS with stored token), and PDF redirect
  (`webNavigation.onBeforeNavigate` on `*.pdf` → `viewer.html?file=<url>`).
- `content.js` + `overlay.css`: full-viewport overlay. Freehand pen (default),
  circle, rectangle tools. Each stroke becomes a mark
  `{type: 'polygon'|'circle'|'rectangle', points|x/y/width/height, role}`.
  After the stroke, an ask panel appears next to the mark: question textarea,
  mic button (Web Speech API, best effort), Ask. Follow-ups reuse the mark.
  Anchor collection: sample a grid inside the mark bbox with
  `document.elementsFromPoint`, dedupe, keep tag/role/text/alt/src/href and
  viewport bbox. Text under the mark is sent as `anchors[].text`.
- `viewer.html` + `viewer.js` + `pdf.js` bundle: renders every page to canvas
  with a text layer; the overlay runs on it like any page. Anchors from text
  layer spans carry `page` and PDF-space bbox.
- `popup.html/js`: StudyOS URL + email/password login → token in
  `chrome.storage.local`; shows last answer; link to StudyOS history.

### 2. API

- `SpatialContext` gains nullable `owner_id`, `page_url`, `page_title`,
  `answer_json`; `goal_id` becomes nullable. Ownership = `owner_id == user`
  or goal owned by user. Dev SQLite bridge + Alembic migration 0010.
- `POST /api/spatial-context/ask` (`SpatialAsk` schema: question, marks,
  canvas, anchors, page{url,title,surface}, image_data, goal_id?,
  privacy_policy, context_id? for follow-ups). Flow:
  1. `resolve_spatial_marks` (existing) → candidates/confidence; polygon marks
     get a bbox so anchor overlap still works.
  2. Build grounding: anchor text (DOM/PDF), goal evidence chunks if goal set,
     optional vision summary.
  3. `spatial_answer()` in `llm.py`: vision-capable route
     (Ollama vision model → OpenAI → Anthropic), else text-only using anchor
     text. Deterministic fallback when no provider: echo what was marked and
     request confirmation. Never performs actions — reference, not authority.
  4. Persist `SpatialContext` with answer; record model event.
  5. Return `{id, answer, confidence, anchors_used, provider, model, resolution}`.
- `POST /api/spatial-context/ask/stream`: SSE wrapper (status → complete).
- `GET /api/spatial-context` returns page/answer fields.
- CORS: allow `chrome-extension://` origins (regex).

### 3. StudyOS shell

Point & Ask view: install instructions (load unpacked from
`apps/extension`, hotkey), recent marks list with page title/url, question,
answer, confidence; "Continue in tutor" sets `spatialId`. Image upload flow
removed.

## Safety and privacy

Mark = reference only. `privacy_policy` controls what leaves the browser:
`anchors_only` (no pixels), `crop_only` (default: crop of marked region),
`full_frame`. Crop capped at 4 MB. Operator telemetry stays metadata-only.

## Testing

- pytest: `/ask` with anchors + no provider → deterministic answer names the
  anchor text; polygon mark normalization; follow-up reuses context;
  ownership 404; list includes page fields.
- JS: `apps/extension/tests/geometry.test.mjs` (node:test) for stroke → bbox
  and anchor scoring.
- Manual: load unpacked, `Alt+Shift+A` on a web page and on a local PDF.
