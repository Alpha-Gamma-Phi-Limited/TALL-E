export type PharmaCategory = "otc" | "supplements";

export const PHARMA_TAXONOMY = {
  categories: ["otc", "supplements"] as PharmaCategory[],
  retailers: ["chemist-warehouse", "bargain-chemist", "life-pharmacy"],
  valueScoreCategories: [] as PharmaCategory[],
};
