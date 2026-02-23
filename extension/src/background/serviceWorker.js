const LATEST_CONTEXT_KEY = "latestContext";

chrome.runtime.onInstalled.addListener(() => {
  console.log("Price Tracker service worker installed.");
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message?.type) {
    return false;
  }

  if (message.type === "PAGE_CONTEXT") {
    const latestContext = message.payload;

    chrome.storage.local.set({ [LATEST_CONTEXT_KEY]: latestContext }, () => {
      if (chrome.runtime.lastError) {
        console.warn("Failed to store latest context", chrome.runtime.lastError);
        sendResponse({ ok: false, error: chrome.runtime.lastError.message });
        return;
      }

      sendResponse({ ok: true });
    });

    return true;
  }

  if (message.type === "GET_LATEST_CONTEXT") {
    chrome.storage.local.get(LATEST_CONTEXT_KEY, (result) => {
      if (chrome.runtime.lastError) {
        sendResponse({ ok: false, error: chrome.runtime.lastError.message });
        return;
      }

      sendResponse({ ok: true, latestContext: result[LATEST_CONTEXT_KEY] ?? null });
    });

    return true;
  }

  return false;
});
