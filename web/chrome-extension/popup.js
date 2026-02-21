const resultsList = document.getElementById("results");
const statusPill = document.getElementById("status");
const searchButton = document.getElementById("search");
const queryInput = document.getElementById("query");
const verticalInput = document.getElementById("vertical");
const budgetInput = document.getElementById("budget");
const openWebButton = document.getElementById("openWeb");

const API_BASE = "http://localhost:8000";
const DASHBOARD_URL = "http://localhost:5173";

const fallbackResults = [
  {
    id: "demo-1",
    name: "Sony WH-1000XM5 Wireless Headphones",
    vertical: "tech",
    category: "Audio",
    best_price_nzd: 529,
    value_score: 92,
    retailer_count: 4
  },
  {
    id: "demo-2",
    name: "Bose QuietComfort Ultra",
    vertical: "tech",
    category: "Audio",
    best_price_nzd: 599,
    value_score: 88,
    retailer_count: 3
  }
];

function setStatus(text) {
  statusPill.textContent = text;
}

function formatPrice(price) {
  return new Intl.NumberFormat("en-NZ", {
    style: "currency",
    currency: "NZD",
    maximumFractionDigits: 0
  }).format(price);
}

function renderResults(items) {
  resultsList.innerHTML = "";

  if (!items.length) {
    resultsList.innerHTML = '<li class="empty-state">No products found for this query.</li>';
    return;
  }

  for (const item of items) {
    const li = document.createElement("li");
    li.className = "result-card";
    li.innerHTML = `
      <h3>${item.name}</h3>
      <div class="meta">
        <span>${item.category ?? "General"}</span>
        <span>${item.retailer_count ?? 0} retailers</span>
      </div>
      <div class="price-row">
        <span class="price">${formatPrice(item.best_price_nzd ?? item.price ?? 0)}</span>
        <span class="score">Value ${Math.round(item.value_score ?? 0)}/100</span>
      </div>
    `;
    resultsList.appendChild(li);
  }
}

async function runSearch() {
  const query = queryInput.value.trim();
  if (!query) {
    setStatus("Add a search term");
    return;
  }

  setStatus("Searching...");
  const params = new URLSearchParams({
    q: query,
    vertical: verticalInput.value,
    page: "1",
    page_size: "5"
  });

  const budget = Number(budgetInput.value);
  if (!Number.isNaN(budget) && budget > 0) {
    params.set("price_max", String(budget));
  }

  try {
    const response = await fetch(`${API_BASE}/v2/products?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const payload = await response.json();
    const items = payload.items ?? [];

    await chrome.storage.local.set({
      lastSearch: {
        query,
        vertical: verticalInput.value,
        budget: budgetInput.value,
        updatedAt: Date.now()
      }
    });

    renderResults(items);
    setStatus(items.length ? `${items.length} matches` : "No matches");
  } catch {
    renderResults(fallbackResults);
    setStatus("Using demo data");
  }
}

async function hydratePreviousSearch() {
  const { lastSearch } = await chrome.storage.local.get("lastSearch");
  if (!lastSearch) {
    renderResults([]);
    return;
  }

  queryInput.value = lastSearch.query ?? "";
  verticalInput.value = lastSearch.vertical ?? "tech";
  budgetInput.value = lastSearch.budget ?? "";

  if (queryInput.value) {
    runSearch();
  } else {
    renderResults([]);
  }
}

searchButton.addEventListener("click", runSearch);
queryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    runSearch();
  }
});
openWebButton.addEventListener("click", async () => {
  await chrome.tabs.create({ url: DASHBOARD_URL });
});

hydratePreviousSearch();
