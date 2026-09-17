# Chrome Web Store listing — Point & Ask

**Name:** StudyOS Point & Ask
**Summary (≤132 chars):** Circle anything on a page or PDF and ask about exactly that. Voice in, voice out, answers saved to your study queue.

**Description**
Stop describing what confuses you. Press Alt+Shift+A, scribble a circle around the equation, diagram, paragraph
or line of code, and ask. Point & Ask reads the text under your mark (and, if you allow it, a small crop of the
region) and answers about that — not the whole page.

- Works on any website and on PDFs (online or downloaded)
- Type or speak your question; hear the answer read aloud
- Follow-up questions keep the same mark
- "Quiz me later" turns an answer into a spaced-repetition review in StudyOS
- Privacy first: choose text-only, crop, or full-tab; never runs on banking/health/government sites
- 20 free asks a day without an account; sign in to keep your history

**Category:** Education · **Language:** English

**Permissions justification**
- `activeTab`, `scripting`: draw the overlay on the tab you invoke it on (hotkey or icon); nothing runs otherwise
- `storage`: your settings and device id
- `offscreen`: record the microphone in Power mode without asking on every site
- `contextMenus`: "Open PDF in Point & Ask viewer"
- `webNavigation`: only acts when the user opts in to "Always open PDFs in the viewer"
- Host permissions `<all_urls>`: the user can circle on any page they choose; the extension is inert until invoked

**Single purpose:** ask questions about a user-selected region of the current page.

**Assets to prepare:** 128×128 icon, 1280×800 screenshots (circle on a textbook page; PDF viewer; voice), 440×280 promo tile,
privacy policy URL (docs/store/PRIVACY_POLICY.md published on the website).

**Build:** `py -3.12 scripts/package_extension.py` → `dist/studyos-point-and-ask-<version>.zip`.

**Review timeline:** submit as *Unlisted* on day 5, expect 3–10 days; move to *Public* after ≥100 beta installs and <2% error rate.
