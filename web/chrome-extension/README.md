# WorthIt Chrome Extension (Frontend Prototype)

This folder contains a frontend-only Google Chrome extension prototype for WorthIt.

## Features

- Popup interface with product search.
- Vertical and budget filters.
- Result cards showing best price and value score.
- Graceful fallback to demo data when API is unavailable.
- Persists last search in `chrome.storage.local`.
- "Open full dashboard" quick link to the main web app.

## Load in Chrome

1. Open Chrome and go to `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select this folder: `web/chrome-extension`.

## Local API integration

The popup fetches from `http://localhost:8000/v2/products`.

Run the API locally before testing live results:

```bash
cd api
uvicorn app.main:app --reload --port 8000
```
