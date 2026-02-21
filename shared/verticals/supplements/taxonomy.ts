export type SupplementsCategory = "protein" | "pre-workout" | "vitamins" | "other";

export const SUPPLEMENTS_TAXONOMY = {
  categories: ["protein", "pre-workout", "vitamins", "other"] as SupplementsCategory[],
  retailers: ["supplements-co-nz", "chemist-warehouse", "bargain-chemist", "mighty-ape"],
  valueScoreCategories: ["protein"] as SupplementsCategory[],
};
