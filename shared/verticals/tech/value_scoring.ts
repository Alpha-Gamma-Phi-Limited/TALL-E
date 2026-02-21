export type ValueScoreInput = {
  category: string;
  attributes: Record<string, unknown>;
  effectivePrice: number | null;
};

const clamp = (n: number) => Math.max(0, Math.min(1, n));
const normalize = (value: number, low: number, high: number) => clamp((value - low) / (high - low));

const asNumber = (v: unknown): number | null => {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

const tier = (v: unknown, map: Record<string, number>) => {
  if (typeof v !== "string") return 0;
  return map[v.toLowerCase()] ?? 0;
};

export const computeValueScore = ({ category, attributes, effectivePrice }: ValueScoreInput): number | null => {
  if (!effectivePrice || effectivePrice <= 0) return null;

  if (category === "laptops") {
    const cpu = asNumber(attributes.cpu_score);
    const ram = asNumber(attributes.ram_gb);
    const storage = asNumber(attributes.storage_gb);
    if (cpu === null || ram === null || storage === null) return null;
    const perf = 0.45 * normalize(cpu, 1000, 10000) + 0.30 * normalize(ram, 4, 64) + 0.25 * normalize(storage, 128, 4000);
    const pricePenalty = normalize(effectivePrice, 700, 4500);
    return clamp(perf * 0.85 + (1 - pricePenalty) * 0.15);
  }

  if (category === "phones") {
    const chipset = tier(attributes.chipset_tier, { entry: 0.4, mid: 0.65, high: 0.85, flagship: 1.0 });
    const ram = asNumber(attributes.ram_gb);
    const storage = asNumber(attributes.storage_gb);
    const battery = asNumber(attributes.battery_mah) ?? 4000;
    if (ram === null || storage === null) return null;
    const perf = 0.4 * chipset + 0.2 * normalize(ram, 4, 16) + 0.25 * normalize(storage, 64, 1024) + 0.15 * normalize(battery, 3000, 6000);
    const pricePenalty = normalize(effectivePrice, 350, 2400);
    return clamp(perf * 0.82 + (1 - pricePenalty) * 0.18);
  }

  if (category === "monitors") {
    const refresh = asNumber(attributes.refresh_rate_hz);
    const panel = tier(attributes.panel_type, { tn: 0.4, ips: 0.75, va: 0.7, oled: 1.0 });
    const resolution = tier(attributes.resolution, { "1080p": 0.55, "1440p": 0.8, "4k": 1.0 });
    if (refresh === null) return null;
    const perf = 0.5 * normalize(refresh, 60, 240) + 0.25 * panel + 0.25 * resolution;
    const pricePenalty = normalize(effectivePrice, 200, 2500);
    return clamp(perf * 0.8 + (1 - pricePenalty) * 0.2);
  }

  return null;
};
