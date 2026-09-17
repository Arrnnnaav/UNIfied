# StudyOS Point & Ask — browser extension

Circle anything you are reading — a website, a web app, a PDF (online or downloaded) — and ask StudyOS about
exactly that region. This is the Spatial Context primitive described in `docs/SPATIAL_CONTEXT.md`, delivered
where students actually read instead of inside the StudyOS shell.

## Install (Chrome / Edge / Brave, unpacked)

1. Open `chrome://extensions`, enable **Developer mode**, click **Load unpacked**, pick this folder (`apps/extension`).
2. For downloaded PDFs (`file:///…pdf`) open the extension's details and enable **Allow access to file URLs**.
3. Press the hotkey. The first time, a consent card explains what leaves the browser and lets you pick
   crop / text-only / full tab. No account needed: 20 asks a day per device; sign in from the icon to keep
   history in StudyOS (anonymous marks move to the account).

## Use

- Press **Alt+Shift+A** (or click the icon → *Start marking on this tab*).
- Scribble a circle with the pen (default), or use the Circle/Box tools. Draw more than one mark if needed.
- Type or dictate (🎤) the question next to the mark: "What is this?", "Why did they do this step?".
- Follow-ups reuse the same mark. **Esc** closes the overlay; **Clear** starts a new context.
- Mark **A Source** then **B Target** to ask relational questions ("how does this feed into that?").
- After an answer the resolved element pulses with a green ring; **Read aloud** speaks it; **Quiz me later**
  puts it in your StudyOS review queue.
- PDFs: right-click → *Open PDF in Point & Ask viewer*, the popup button, or tick *Always open PDFs in the viewer*.
- **Power mode** (popup): choose the model provider and use server speech (faster-whisper / pocket-tts) instead
  of the browser voice. Chrome asks for the microphone once via `permission.html`.
- Never runs on banking, payment, health or government sites (plus your own blocklist in the popup).

## What gets sent

Marks in viewport coordinates, the DOM/PDF text under the mark ("anchors"), page title/URL, and — depending on the
privacy setting in the popup — a crop of the marked region (default), nothing but text, or the whole visible tab.
Marks are a reference, never authority: StudyOS explains what you marked; it never acts on the page.

## Development

```bash
node --test tests/geometry.test.mjs
py -3.12 ../../scripts/sync_spatial.py --check     # same code ships as the standalone Spatial extension
py -3.12 ../../scripts/package_extension.py        # dist/*.zip for the Chrome Web Store
```

`config.js` is the only file that differs from `D:/PROJECTS/Spatial/extension` (mode, API base, paths,
feature flags); `dev/harness.html` runs the overlay against a local server with `chrome.*` stubbed.

`vendor/` holds pdf.js 4.10.38 (Apache-2.0, see `vendor/LICENSE`).
