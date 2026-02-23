function hashString(input) {
  let hash = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function seededValue(seed, min, max) {
  const range = max - min + 1;
  return min + (seed % range);
}

function formatCents(cents) {
  return `$${(cents / 100).toFixed(2)}`;
}

function detectStore(url) {
  try {
    const hostname = new URL(url).hostname.replace(/^www\./, "");
    const parts = hostname.split(".");
    return {
      name: parts[0]
        .split("-")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" "),
      detectedFromUrl: hostname,
    };
  } catch {
    return { name: "Unknown Store", detectedFromUrl: "invalid-url" };
  }
}

function buildHistory(baseCents, seed) {
  const points = [];
  const today = new Date();

  for (let i = 0; i < 12; i += 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - (11 - i) * 7);
    const delta = ((seed >> (i % 16)) % 900) - 450;
    points.push({
      date: date.toISOString().slice(0, 10),
      priceCents: Math.max(999, baseCents + delta),
    });
  }

  return points;
}

export async function mockLookup(url, title) {
  const source = `${url}|${title}`;
  const seed = hashString(source);

  const priceCents = seededValue(seed, 1499, 45999);
  const brandPool = ["Acme", "Nova", "Orbit", "Vertex", "Everline", "Summit"];
  const sizePool = ["250ml", "500g", "1L", "2-pack", "Standard", "Large"];

  const store = detectStore(url);
  const brand = brandPool[seed % brandPool.length];
  const size = sizePool[(seed >> 4) % sizePool.length];

  const response = {
    store,
    product: {
      name: title?.trim() || "Unknown Product",
      brand,
      size,
      matchedBy: "title+url-hash",
    },
    currentPrice: {
      cents: priceCents,
      display: formatCents(priceCents),
      capturedAt: new Date().toISOString(),
    },
    history: buildHistory(priceCents, seed),
    compare: [
      { store: "Shop Alpha", priceCents: Math.max(999, priceCents - 220), display: formatCents(Math.max(999, priceCents - 220)) },
      { store: "Shop Beta", priceCents: priceCents + 180, display: formatCents(priceCents + 180) },
      { store: "Shop Gamma", priceCents: Math.max(999, priceCents - 90), display: formatCents(Math.max(999, priceCents - 90)) },
    ],
  };

  await new Promise((resolve) => setTimeout(resolve, 180));
  return response;
}
