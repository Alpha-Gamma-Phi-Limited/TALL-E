export type HomeAppliancesCategory = "fridges" | "washing-machines" | "dishwashers" | "appliances";

export const HOME_APPLIANCES_TAXONOMY = {
  categories: ["fridges", "washing-machines", "dishwashers", "appliances"] as HomeAppliancesCategory[],
  retailers: ["noel-leeming", "harvey-norman", "farmers", "heathcotes", "mighty-ape", "the-warehouse"],
  valueScoreCategories: ["fridges", "washing-machines", "dishwashers"] as HomeAppliancesCategory[],
};
