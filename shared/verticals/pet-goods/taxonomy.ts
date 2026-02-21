export type PetGoodsCategory = "pet-food" | "treats" | "flea-tick" | "grooming" | "toys" | "bedding" | "pet-supplies";

export const PET_GOODS_TAXONOMY = {
  categories: ["pet-food", "treats", "flea-tick", "grooming", "toys", "bedding", "pet-supplies"] as PetGoodsCategory[],
  retailers: ["animates", "petdirect", "pet-co-nz"],
  valueScoreCategories: [] as PetGoodsCategory[],
};
