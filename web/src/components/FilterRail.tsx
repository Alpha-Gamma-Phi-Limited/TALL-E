import { MetaResponse } from "../api/client";
import { ProductFilters } from "../hooks/useProductSearchParams";

type Props = {
  filters: ProductFilters;
  setFilters: (patch: Partial<ProductFilters>) => void;
  meta: MetaResponse | null;
};

export default function FilterRail({ filters, setFilters, meta }: Props) {
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
    <aside className="filter-rail">
      <div className="filter-head">
        <h2>Filter Rail</h2>
        <button onClick={() => setFilters({ category: "", brand: "", retailers: "", promo_only: false })}>Clear</button>
      </div>

      <label>
        Category
        <select value={filters.category} onChange={(e) => setFilters({ category: e.target.value })}>
          <option value="">All categories</option>
          {(meta?.categories ?? []).map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </label>

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

      <div className="retailer-picker">
        <p>Retailers</p>
        <div className="retailer-list">
          {(meta?.retailers ?? []).map((retailer) => {
            const active = selectedRetailers.has(retailer.slug);
            return (
              <button
                key={retailer.slug}
                className={`retailer-pill ${active ? "is-active" : ""}`}
                onClick={() => toggleRetailer(retailer.slug)}
              >
                {retailer.name}
              </button>
            );
          })}
        </div>
      </div>

      <div className="active-filters">
        <p>Active filters</p>
        <span>{filters.category || "Any category"}</span>
        <span>{filters.brand || "Any brand"}</span>
        <span>{filters.promo_only ? "Promo only" : "All price types"}</span>
      </div>
    </aside>
  );
}
