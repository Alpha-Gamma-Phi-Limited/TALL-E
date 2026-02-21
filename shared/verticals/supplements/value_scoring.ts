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

  if (category === "protein") {
    const protein = asNumber(attributes.protein_per_serving_g);
    const servings = asNumber(attributes.servings);
    if (protein === null || servings === null) return null;
    
    const score = 0.6 * normalize(protein, 15, 30) + 0.4 * normalize(servings, 10, 100);
    const pricePenalty = normalize(effectivePrice, 30, 200);
    return clamp(score * 0.8 + (1 - pricePenalty) * 0.2);
  }

  return null;
};
