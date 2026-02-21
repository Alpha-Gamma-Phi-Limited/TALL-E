import { useEffect, useMemo, useState } from "react";

import { fetchMeta, fetchProductDetail, fetchProducts, MetaResponse, ProductDetail, ProductsResponse } from "./api/client";
import CommandBar from "./components/CommandBar";
import DataGrid from "./components/DataGrid";
import InspectorPanel from "./components/InspectorPanel";
import { useProductSearchParams, Vertical } from "./hooks/useProductSearchParams";

const verticalTabs = [
  { key: "tech", label: "Technology", enabled: true },
  { key: "pharma", label: "Pharma", enabled: true },
  { key: "beauty", label: "Beauty", enabled: true },
  { key: "sport", label: "Sport", enabled: false },
] as const;

export default function App() {
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
    if (filters.vertical !== "tech" && filters.sort === "value_desc") {
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
          if (response.items.length === 0) {
            setSelectedId(null);
          }
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoadingProducts(false));
    }, 220);

    return () => window.clearTimeout(timer);
  }, [filters]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    setLoadingDetail(true);
    fetchProductDetail(selectedId, filters.vertical)
      .then(setDetail)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingDetail(false));
  }, [selectedId, filters.vertical]);

  const totalPages = Math.max(1, Math.ceil(products.total / Math.max(filters.page_size, 1)));
  const canGoNext = filters.page < totalPages;

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.q) count += 1;
    if (filters.category) count += 1;
    if (filters.brand) count += 1;
    if (filters.retailers) count += 1;
    if (filters.promo_only) count += 1;
    return count;
  }, [filters]);

  return (
    <div className="apple-shell">
      <section className="hero" id="about">
        <h1>TALL-E</h1>
        <h2>General price comparison across major New Zealand retailers.</h2>

        <div className="vertical-subbar" role="tablist" aria-label="Vertical selector">
          {verticalTabs.map((tab) => {
            const isActive = filters.vertical === tab.key;
            const isDisabled = !tab.enabled;
            return (
              <button
                key={tab.key}
                className={`vertical-tab ${isActive ? "is-active" : ""}`}
                disabled={isDisabled}
                title={isDisabled ? "Coming soon" : undefined}
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
                {isDisabled && <span>Coming soon</span>}
              </button>
            );
          })}
        </div>

        <p>{meta ? `Currently tracking ${meta.retailers.length} retailers in this vertical.` : ""}</p>
      </section>

      <CommandBar filters={filters} setFilters={setFilters} total={products.total} meta={meta} />

      {error && <div className="error-banner">{error}</div>}

      <section className="results-head" id="products">
        <div>
          <strong>{products.total.toLocaleString()}</strong>
          <span>products</span>
        </div>
        <div>
          <strong>{activeFilterCount}</strong>
          <span>active filters</span>
        </div>
        <div>
          <strong>{meta?.categories.length ?? 0}</strong>
          <span>categories</span>
        </div>
      </section>

      <section className="products-area">
        {loadingProducts ? (
          <div className="loading-state">Loading products…</div>
        ) : (
          <DataGrid items={products.items} selectedId={selectedId} onSelect={setSelectedId} />
        )}
      </section>

      <footer className="pagination-row" id="compare">
        <button disabled={filters.page <= 1} onClick={() => setFilters({ page: filters.page - 1 })}>
          Previous
        </button>
        <span>
          Page {filters.page} of {totalPages}
        </span>
        <button disabled={!canGoNext} onClick={() => setFilters({ page: filters.page + 1 })}>
          Next
        </button>
      </footer>

      <InspectorPanel product={detail} loading={loadingDetail} onClose={() => setSelectedId(null)} />
    </div>
  );
}
