(() => {
  let lastSentKey = "";

  function getPageContext() {
    return {
      url: window.location.href,
      title: document.title,
      capturedAt: new Date().toISOString(),
    };
  }

  function sendPageContext() {
    const context = getPageContext();
    const dedupeKey = `${context.url}|${context.title}`;

    if (dedupeKey === lastSentKey) {
      return;
    }

    lastSentKey = dedupeKey;

    chrome.runtime.sendMessage({ type: "PAGE_CONTEXT", payload: context }, () => {
      if (chrome.runtime.lastError) {
        // Service worker may be sleeping; Chrome retries as it wakes.
      }
    });
  }

  function patchHistoryMethod(methodName) {
    const original = history[methodName];
    history[methodName] = function patchedHistoryMethod(...args) {
      const result = original.apply(this, args);
      setTimeout(sendPageContext, 50);
      return result;
    };
  }

  patchHistoryMethod("pushState");
  patchHistoryMethod("replaceState");

  window.addEventListener("popstate", () => setTimeout(sendPageContext, 50));
  window.addEventListener("hashchange", () => setTimeout(sendPageContext, 50));
  window.addEventListener("load", sendPageContext);

  const titleObserver = new MutationObserver(() => setTimeout(sendPageContext, 0));
  const titleNode = document.querySelector("title");
  if (titleNode) {
    titleObserver.observe(titleNode, { childList: true });
  }

  sendPageContext();
})();
