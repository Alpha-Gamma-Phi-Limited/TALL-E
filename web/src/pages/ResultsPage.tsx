import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMeta, fetchProductDetail, fetchProducts, MetaResponse, ProductDetail, ProductsResponse } from "../api/client";
import SearchBar from "../components/SearchBar";
import DataGrid from "../components/DataGrid";
import InspectorPanel from "../components/InspectorPanel";
import { useProductSearchParams, Vertical } from "../hooks/useProductSearchParams";

const verticalTabs = [
  { key: "tech", label: "Technology", enabled: true },
  { key: "home-appliances", label: "Home & Appliances", enabled: true },
  { key: "pharmaceuticals", label: "Pharmaceuticals", enabled: true },
  { key: "supplements", label: "Supplements", enabled: true },
  { key: "beauty", label: "Beauty", enabled: true },
  { key: "pet-goods", label: "Pet Goods", enabled: true },
] as const;

export default function ResultsPage() {
  const { filters, setFilters, defaultSortByVertical } = useProductSearchParams();
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [products, setProducts] = useState<ProductsResponse>({ items: [], total: 0, page: 1, page_size: 24 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    fetchMeta(filters.vertical).then(setMeta).catch((err: Error) => setError(err.message));
  }, [filters.vertical]);

  useEffect(() => {
    const supportsValueSort =
      filters.vertical === "tech" || filters.vertical === "home-appliances" || filters.vertical === "supplements";
    if (!supportsValueSort && filters.sort === "value_desc") {
      setFilters({ sort: defaultSortByVertical[filters.vertical] });
    }
  }, [defaultSortByVertical, filters.sort, filters.vertical, setFilters]);

  useEffect(() => {
    setLoadingProducts(true);
    setError(null);
    const timer = window.setTimeout(() => {
      fetchProducts(filters)
        .then((response) => {
          setProducts(response);
          if (response.items.length === 0) setSelectedId(null);
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoadingProducts(false));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [filters]);

  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    setLoadingDetail(true);
    fetchProductDetail(selectedId, filters.vertical)
      .then(setDetail)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingDetail(false));
  }, [selectedId, filters.vertical]);

  const selectedRetailers = new Set(
    filters.retailers.split(",").map((s) => s.trim()).filter(Boolean)
  );

  const toggleRetailer = (slug: string) => {
    const next = new Set(selectedRetailers);
    if (next.has(slug)) next.delete(slug); else next.add(slug);
    setFilters({ retailers: Array.from(next).join(",") });
  };

  const totalPages = Math.max(1, Math.ceil(products.total / Math.max(filters.page_size, 1)));
  const canGoNext = filters.page < totalPages;
  const supportsValueSort =
    filters.vertical === "tech" || filters.vertical === "home-appliances" || filters.vertical === "supplements";

  return (
    <div className="results-shell">
      <aside className="results-sidebar">
        <Link to="/" className="sidebar-logo">TALL-E</Link>

        <h4 className="sidebar-heading">Category</h4>
        <ul className="category-list">
          <li>
            <button
              className={`category-item ${!filters.category ? "is-active" : ""}`}
              onClick={() => setFilters({ category: "" })}
            >
              All
            </button>
          </li>
          {(meta?.categories ?? []).map((cat) => (
            <li key={cat}>
              <button
                className={`category-item ${filters.category === cat ? "is-active" : ""}`}
                onClick={() => setFilters({ category: cat })}
              >
                {cat}
              </button>
            </li>
          ))}
        </ul>

        {(meta?.brands ?? []).length > 0 && (
          <>
            <h4 className="sidebar-heading">Brand</h4>
            <ul className="category-list">
              <li>
                <button
                  className={`category-item ${!filters.brand ? "is-active" : ""}`}
                  onClick={() => setFilters({ brand: "" })}
                >
                  All
                </button>
              </li>
              {(meta?.brands ?? []).map((brand) => (
                <li key={brand}>
                  <button
                    className={`category-item ${filters.brand === brand ? "is-active" : ""}`}
                    onClick={() => setFilters({ brand })}
                  >
                    {brand}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        {(meta?.retailers ?? []).length > 0 && (
          <>
            <h4 className="sidebar-heading">Retailer</h4>
            <div className="sidebar-chips">
              {(meta?.retailers ?? []).map((retailer) => (
                <button
                  key={retailer.slug}
                  className={`retailer-chip ${selectedRetailers.has(retailer.slug) ? "active" : ""}`}
                  onClick={() => toggleRetailer(retailer.slug)}
                >
                  {retailer.name}
                </button>
              ))}
            </div>
          </>
        )}

        <button
          className={`promo-switch sidebar-promo ${filters.promo_only ? "active" : ""}`}
          onClick={() => setFilters({ promo_only: !filters.promo_only })}
        >
          On sale only
        </button>
      </aside>

      <div className="results-right">
        <header className="results-header">
          <SearchBar filters={filters} setFilters={setFilters} autoFocus={!!filters.q} />
        </header>

        <div className="results-subnav">
          <div className="vertical-subbar small" role="tablist" aria-label="Vertical selector">
            {verticalTabs.map((tab) => {
              const isActive = filters.vertical === tab.key;
              const isDisabled = !tab.enabled;
              return (
                <button
                  key={tab.key}
                  className={`vertical-tab ${isActive ? "is-active" : ""}`}
                  disabled={isDisabled}
                  onClick={() => {
                    if (!tab.enabled) return;
                    const nextVertical = tab.key as Vertical;
                    setSelectedId(null);
                    setFilters({
                      vertical: nextVertical,
                      category: "",
                      brand: "",
                      retailers: "",
                      sort: defaultSortByVertical[nextVertical],
                      promo_only: false,
                    });
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="results-toolbar">
          <span className="result-count">{products.total.toLocaleString()} products</span>
          <select
            className="sort-select"
            value={filters.sort}
            onChange={(e) => setFilters({ sort: e.target.value })}
          >
            {supportsValueSort && <option value="value_desc">Best Value</option>}
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="discount_desc">Biggest Discount</option>
            <option value="relevance">Relevance</option>
          </select>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <section className="products-area">
          {loadingProducts ? (
            <div className="loading-state">Loading products…</div>
          ) : (
            <DataGrid items={products.items} selectedId={selectedId} onSelect={setSelectedId} />
          )}
        </section>

        <footer className="pagination-row">
          <button disabled={filters.page <= 1} onClick={() => setFilters({ page: filters.page - 1 })}>
            Previous
          </button>
          <span>Page {filters.page} of {totalPages}</span>
          <button disabled={!canGoNext} onClick={() => setFilters({ page: filters.page + 1 })}>
            Next
          </button>
        </footer>
      </div>

      <InspectorPanel product={detail} loading={loadingDetail} onClose={() => setSelectedId(null)} />
    </div>
  );
}
