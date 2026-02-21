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

export const computeValueScore = ({ category, attributes, effectivePrice }: ValueScoreInput): number | null => {
  if (!effectivePrice || effectivePrice <= 0) return null;

  if (category === "fridges") {
    const capacity = asNumber(attributes.capacity_l);
    const energy = asNumber(attributes.energy_rating);
    if (capacity === null) return null;
    const score = 0.5 * normalize(capacity, 200, 1000) + 0.5 * (energy ? normalize(energy, 1, 6) : 0.5);
    const pricePenalty = normalize(effectivePrice, 500, 5000);
    return clamp(score * 0.8 + (1 - pricePenalty) * 0.2);
  }

  if (category === "washing-machines") {
    const capacity = asNumber(attributes.capacity_kg);
    const energy = asNumber(attributes.energy_rating);
    if (capacity === null) return null;
    const score = 0.5 * normalize(capacity, 5, 16) + 0.5 * (energy ? normalize(energy, 1, 6) : 0.5);
    const pricePenalty = normalize(effectivePrice, 400, 3000);
    return clamp(score * 0.8 + (1 - pricePenalty) * 0.2);
  }

  if (category === "dishwashers") {
    const settings = asNumber(attributes.place_settings);
    const energy = asNumber(attributes.energy_rating);
    if (settings === null) return null;
    const score = 0.5 * normalize(settings, 6, 16) + 0.5 * (energy ? normalize(energy, 1, 6) : 0.5);
    const pricePenalty = normalize(effectivePrice, 500, 2500);
    return clamp(score * 0.8 + (1 - pricePenalty) * 0.2);
  }

  return null;
};
