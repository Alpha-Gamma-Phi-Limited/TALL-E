import { mockLookup } from "../shared/mockLookup.js";

const DATA_MODE = "mock"; // "mock" | "api"
const API_BASE = "http://localhost:8000";

const els = {
  modePill: document.getElementById("modePill"),
  contextTitle: document.getElementById("contextTitle"),
  contextUrl: document.getElementById("contextUrl"),
  loadingState: document.getElementById("loadingState"),
  detectedProduct: document.getElementById("detectedProduct"),
  currentPrice: document.getElementById("currentPrice"),
  similarImage: document.getElementById("similarImage"),
  similarStore: document.getElementById("similarStore"),
  sliderMeta: document.getElementById("sliderMeta"),
  prevBtn: document.getElementById("prevBtn"),
  nextBtn: document.getElementById("nextBtn"),
  statLow: document.getElementById("statLow"),
  statAvg: document.getElementById("statAvg"),
  statHigh: document.getElementById("statHigh"),
  lowPoints: document.getElementById("lowPoints"),
  historyCanvas: document.getElementById("historyCanvas"),
  jsonOutput: document.getElementById("jsonOutput"),
  refreshBtn: document.getElementById("refreshBtn"),
  copyBtn: document.getElementById("copyBtn"),
  message: document.getElementById("message"),
};

let latestContext = null;
let latestResponse = null;
let carouselItems = [];
let carouselIndex = 0;

function setLoading(isLoading) {
  els.loadingState.hidden = !isLoading;
  els.refreshBtn.disabled = isLoading;
}

function setMessage(text) {
  els.message.textContent = text;
}

function sendRuntimeMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response);
    });
  });
}

function formatMoney(cents) {
  return `$${(cents / 100).toFixed(2)}`;
}

function buildImageSeed(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash << 5) - hash + text.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function buildPlaceholderImage(item) {
  const seed = buildImageSeed(item.name + item.store);
  const hue = seed % 360;
  const bg = `hsl(${hue}, 38%, 86%)`;
  const fg = `hsl(${(hue + 190) % 360}, 44%, 28%)`;
  const text = `${item.store} • ${item.display}`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="360"><rect width="100%" height="100%" fill="${bg}"/><rect x="22" y="22" width="556" height="316" rx="16" fill="rgba(255,255,255,0.58)"/><text x="40" y="170" font-size="28" fill="${fg}" font-family="Arial, sans-serif">${item.name}</text><text x="40" y="210" font-size="22" fill="${fg}" font-family="Arial, sans-serif">${text}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function buildCarouselData(response) {
  const base = {
    name: response?.product?.name || "Unknown product",
    store: response?.store?.name || "Current store",
    display: response?.currentPrice?.display || "—",
    cents: response?.currentPrice?.cents || 0,
  };

  const compare = (response?.compare || []).map((item, idx) => ({
    name: `${base.name} (alt ${idx + 1})`,
    store: item.store,
    display: item.display,
    cents: item.priceCents,
  }));

  return [base, ...compare].map((item) => ({
    ...item,
    image: buildPlaceholderImage(item),
  }));
}

function renderCarouselItem() {
  if (!carouselItems.length) {
    els.sliderMeta.textContent = "Item 0 of 0";
    els.similarStore.textContent = "Store";
    els.detectedProduct.textContent = "—";
    els.currentPrice.textContent = "—";
    els.similarImage.src = "";
    return;
  }

  const item = carouselItems[carouselIndex];
  els.sliderMeta.textContent = `Item ${carouselIndex + 1} of ${carouselItems.length}`;
  els.similarStore.textContent = item.store;
  els.detectedProduct.textContent = item.name;
  els.currentPrice.textContent = item.display;
  els.similarImage.src = item.image;
}

function renderHistoryGraph(history) {
  const canvas = els.historyCanvas;
  const ctx = canvas.getContext("2d");
  if (!ctx || !history?.length) {
    els.statLow.textContent = "Lowest: —";
    els.statAvg.textContent = "Average: —";
    els.statHigh.textContent = "Highest: —";
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#0a2240";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
    return;
  }

  const values = history.map((point) => point.priceCents);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const avg = Math.round(values.reduce((sum, n) => sum + n, 0) / values.length);

  els.statLow.textContent = `Lowest: ${formatMoney(min)}`;
  els.statAvg.textContent = `Average: ${formatMoney(avg)}`;
  els.statHigh.textContent = `Highest: ${formatMoney(max)}`;

  const width = canvas.width;
  const height = canvas.height;
  const pad = 12;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#0a2240";
  ctx.fillRect(0, 0, width, height);

  function yScale(value) {
    if (max === min) return height / 2;
    const ratio = (value - min) / (max - min);
    return height - pad - ratio * (height - pad * 2);
  }

  const lowY = yScale(min);
  const avgY = yScale(avg);
  const highY = yScale(max);

  ctx.strokeStyle = "rgba(42, 210, 111, 0.5)";
  ctx.beginPath();
  ctx.moveTo(0, lowY);
  ctx.lineTo(width, lowY);
  ctx.stroke();

  ctx.strokeStyle = "rgba(244, 207, 87, 0.55)";
  ctx.beginPath();
  ctx.moveTo(0, avgY);
  ctx.lineTo(width, avgY);
  ctx.stroke();

  ctx.strokeStyle = "rgba(255, 122, 69, 0.6)";
  ctx.beginPath();
  ctx.moveTo(0, highY);
  ctx.lineTo(width, highY);
  ctx.stroke();

  const xStep = (width - pad * 2) / Math.max(1, history.length - 1);

  ctx.beginPath();
  history.forEach((point, idx) => {
    const x = pad + idx * xStep;
    const y = yScale(point.priceCents);
    if (idx === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.strokeStyle = "#2ed6ff";
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.lineTo(width - pad, height - pad);
  ctx.lineTo(pad, height - pad);
  ctx.closePath();
  ctx.fillStyle = "rgba(46, 214, 255, 0.13)";
  ctx.fill();
}

function renderLowPoints(history) {
  if (!history?.length) {
    els.lowPoints.innerHTML = "<li>No history yet.</li>";
    return;
  }

  const sorted = [...history].sort((a, b) => a.priceCents - b.priceCents).slice(0, 3);
  els.lowPoints.innerHTML = sorted
    .map((point) => `<li>${point.date}: drops to ${formatMoney(point.priceCents)}</li>`)
    .join("");
}

function renderContext(context) {
  els.contextTitle.textContent = context?.title || "No page context captured yet.";
  els.contextUrl.textContent = context?.url || "—";
}

function renderResult(data) {
  latestResponse = data;
  carouselItems = buildCarouselData(data);
  carouselIndex = 0;
  renderCarouselItem();
  renderHistoryGraph(data?.history || []);
  renderLowPoints(data?.history || []);
  els.jsonOutput.textContent = JSON.stringify(data || {}, null, 2);
}

async function fetchLookup(url, title) {
  if (DATA_MODE === "api") {
    const params = new URLSearchParams({ url, title });
    const response = await fetch(`${API_BASE}/lookup?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Lookup API failed: ${response.status}`);
    }
    return response.json();
  }
  return mockLookup(url, title);
}

async function runLookup() {
  if (!latestContext?.url) {
    renderResult({});
    setMessage("Open a product page and refresh.");
    return;
  }

  setMessage("");
  setLoading(true);
  try {
    const data = await fetchLookup(latestContext.url, latestContext.title || "");
    renderResult(data);
  } catch (error) {
    console.error(error);
    setMessage("Lookup failed. Please try again.");
  } finally {
    setLoading(false);
  }
}

async function initializePopup() {
  els.modePill.textContent = DATA_MODE === "mock" ? "Mock" : "API";
  try {
    const response = await sendRuntimeMessage({ type: "GET_LATEST_CONTEXT" });
    latestContext = response?.latestContext || null;
    if (!latestContext) {
      renderContext(null);
      renderResult({});
      setMessage("Open a product page and refresh.");
      return;
    }
    renderContext(latestContext);
    await runLookup();
  } catch (error) {
    console.error(error);
    setMessage("Unable to reach extension background worker.");
  }
}

els.prevBtn.addEventListener("click", () => {
  if (!carouselItems.length) return;
  carouselIndex = (carouselIndex - 1 + carouselItems.length) % carouselItems.length;
  renderCarouselItem();
});

els.nextBtn.addEventListener("click", () => {
  if (!carouselItems.length) return;
  carouselIndex = (carouselIndex + 1) % carouselItems.length;
  renderCarouselItem();
});

els.refreshBtn.addEventListener("click", async () => {
  try {
    const response = await sendRuntimeMessage({ type: "GET_LATEST_CONTEXT" });
    latestContext = response?.latestContext || latestContext;
    renderContext(latestContext);
  } catch (error) {
    console.error(error);
  }
  await runLookup();
});

els.copyBtn.addEventListener("click", async () => {
  if (!latestResponse) {
    setMessage("Nothing to copy yet.");
    return;
  }
  try {
    await navigator.clipboard.writeText(JSON.stringify(latestResponse, null, 2));
    setMessage("JSON copied to clipboard.");
  } catch (error) {
    console.error(error);
    setMessage("Copy failed. Clipboard permission may be blocked.");
  }
});

initializePopup();
