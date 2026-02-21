export type PharmaceuticalsCategory = "otc" | "supplements";

export const PHARMACEUTICALS_TAXONOMY = {
  categories: ["otc", "supplements"] as PharmaceuticalsCategory[],
  retailers: ["chemist-warehouse", "bargain-chemist", "life-pharmacy", "mighty-ape", "the-warehouse"],
  valueScoreCategories: [] as PharmaceuticalsCategory[],
};
