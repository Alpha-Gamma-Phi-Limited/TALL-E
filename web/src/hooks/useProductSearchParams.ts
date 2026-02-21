import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export type Vertical = "tech" | "pharma";

export type ProductFilters = {
  vertical: Vertical;
  q: string;
  category: string;
  brand: string;
  retailers: string;
  promo_only: boolean;
  sort: string;
  page: number;
  page_size: number;
};

const DEFAULTS: ProductFilters = {
  vertical: "tech",
  q: "",
  category: "",
  brand: "",
  retailers: "",
  promo_only: false,
  sort: "value_desc",
  page: 1,
  page_size: 24,
};

const DEFAULT_SORT_BY_VERTICAL: Record<Vertical, string> = {
  tech: "value_desc",
  pharma: "price_asc",
};

function parseVertical(value: string | null): Vertical {
  return value === "pharma" ? "pharma" : "tech";
}

export function useProductSearchParams() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<ProductFilters>(() => {
    const vertical = parseVertical(searchParams.get("vertical"));
    return {
      vertical,
      q: searchParams.get("q") ?? DEFAULTS.q,
      category: searchParams.get("category") ?? DEFAULTS.category,
      brand: searchParams.get("brand") ?? DEFAULTS.brand,
      retailers: searchParams.get("retailers") ?? DEFAULTS.retailers,
      promo_only: searchParams.get("promo_only") === "true",
      sort: searchParams.get("sort") ?? DEFAULT_SORT_BY_VERTICAL[vertical],
      page: Number(searchParams.get("page") ?? DEFAULTS.page),
      page_size: Number(searchParams.get("page_size") ?? DEFAULTS.page_size),
    };
  }, [searchParams]);

  const setFilters = (patch: Partial<ProductFilters>) => {
    const next = new URLSearchParams(searchParams);
    Object.entries(patch).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "" || value === false) {
        next.delete(key);
      } else {
        next.set(key, String(value));
      }
    });

    const nextVertical = parseVertical(next.get("vertical"));
    if (!next.get("sort")) {
      next.set("sort", DEFAULT_SORT_BY_VERTICAL[nextVertical]);
    }

    if (
      patch.vertical !== undefined ||
      patch.q !== undefined ||
      patch.category !== undefined ||
      patch.brand !== undefined ||
      patch.retailers !== undefined
    ) {
      next.set("page", "1");
    }

    setSearchParams(next);
  };

  return { filters, setFilters, defaultSortByVertical: DEFAULT_SORT_BY_VERTICAL };
}
