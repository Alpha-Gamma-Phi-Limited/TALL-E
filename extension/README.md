# Price Tracker Chrome Extension (MVP)

Manifest V3 Chrome extension MVP that captures active page context (URL + title), stores it in the background service worker, and renders a mock pricing experience in the popup.

## Folder layout

```
extension/
  manifest.json
  src/
    background/serviceWorker.js
    content/contentScript.js
    popup/popup.html
    popup/popup.js
    popup/popup.css
    shared/mockLookup.js
    shared/types.js
```

## Load unpacked in Chrome

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension/` directory.

## Test flow

1. Visit any webpage.
2. Refresh that tab once to ensure context is captured.
3. Open the extension popup.
4. Confirm the popup shows:
   - Header with logo + mode pill.
   - Similar-products slider section.
   - Price history graph section.
   - Historic cheap points list.
   - Raw JSON details block.
5. Use **Refresh** to re-run lookup and **Copy JSON** to copy payload.

## Where to edit

- UI structure/text: `src/popup/popup.html`
- Styles/theme: `src/popup/popup.css`
- Popup logic (slider/graph/messaging): `src/popup/popup.js`
- Mock response model: `src/shared/mockLookup.js`
- Context capture behavior: `src/content/contentScript.js`

## Future backend swap

`src/popup/popup.js` has:

```js
const DATA_MODE = "mock"; // switch to "api" when backend is ready
const API_BASE = "http://localhost:8000";
```

When `DATA_MODE === "api"`, the popup uses:

```js
fetch(`${API_BASE}/lookup?url=...&title=...`)
```

Keep response shape compatible with the mock schema so the popup rendering remains unchanged.


## Note on icons and PR tooling

Binary icon files are intentionally omitted in this branch to avoid PR tools that reject binary attachments. If you need icons later, add PNGs and re-enable the `icons` field in `manifest.json`.
