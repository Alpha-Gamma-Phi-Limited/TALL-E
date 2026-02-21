import { MetaResponse } from "../api/client";
import { ProductFilters } from "../hooks/useProductSearchParams";

type Props = {
  filters: ProductFilters;
  setFilters: (patch: Partial<ProductFilters>) => void;
  total: number;
  meta: MetaResponse | null;
};

export default function CommandBar({ filters, setFilters, total, meta }: Props) {
  const selectedRetailers = new Set(
    filters.retailers
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  );

  const toggleRetailer = (slug: string) => {
    const next = new Set(selectedRetailers);
    if (next.has(slug)) {
      next.delete(slug);
    } else {
      next.add(slug);
    }
    setFilters({ retailers: Array.from(next).join(",") });
  };

  return (
    <section className="controls-wrap">
      <div className="control-row">
        <label>
          Brand
          <select value={filters.brand} onChange={(e) => setFilters({ brand: e.target.value })}>
            <option value="">All brands</option>
            {(meta?.brands ?? []).map((brand) => (
              <option key={brand} value={brand}>
                {brand}
              </option>
            ))}
          </select>
        </label>

        <label>
          Sort
          <select value={filters.sort} onChange={(e) => setFilters({ sort: e.target.value })}>
            {(filters.vertical === "tech" || filters.vertical === "home-appliances" || filters.vertical === "supplements") && (
              <option value="value_desc">Best Value</option>
            )}
            <option value="price_asc">Price Low to High</option>
            <option value="price_desc">Price High to Low</option>
            <option value="discount_desc">Biggest Discount</option>
            <option value="relevance">Relevance</option>
          </select>
        </label>

        <button
          className={`promo-switch ${filters.promo_only ? "active" : ""}`}
          onClick={() => setFilters({ promo_only: !filters.promo_only })}
        >
          Promo only
        </button>
      </div>

      <div className="retailer-row">
        {(meta?.retailers ?? []).map((retailer) => {
          const active = selectedRetailers.has(retailer.slug);
          return (
            <button
              key={retailer.slug}
              className={`retailer-chip ${active ? "active" : ""}`}
              onClick={() => toggleRetailer(retailer.slug)}
            >
              {retailer.name}
            </button>
          );
        })}
      </div>
    </section>
  );
}
