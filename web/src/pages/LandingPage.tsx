import { useNavigate } from "react-router-dom";
import { Vertical } from "../hooks/useProductSearchParams";
import SearchBar from "../components/SearchBar";
import DataGrid from "../components/DataGrid";
import { useEffect, useState } from "react";
import { fetchProducts, ProductListItem } from "../api/client";

const verticalTabs = [
  { key: "tech", label: "Technology", enabled: true },
  { key: "home-appliances", label: "Home & Appliances", enabled: true },
  { key: "pharmaceuticals", label: "Pharmaceuticals", enabled: true },
  { key: "supplements", label: "Supplements", enabled: true },
  { key: "beauty", label: "Beauty", enabled: true },
  { key: "pet-goods", label: "Pet Goods", enabled: true },
] as const;

export default function LandingPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [vertical, setVertical] = useState<Vertical>("tech");
  const [featured, setFeatured] = useState<ProductListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchProducts({ vertical: vertical, page_size: 10, sort: vertical === "pet-goods" || vertical === "pharmaceuticals" || vertical === "beauty" ? "price_asc" : "value_desc" })
      .then((res) => setFeatured(res.items))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [vertical]);

  const handleSearch = (query: string) => {
    navigate(`/search?vertical=${vertical}&q=${encodeURIComponent(query)}`);
  };

  return (
    <div className="landing-shell">
      <section className="hero">
        <h1>TALL-E</h1>
        <h2>Price comparison across major New Zealand retailers.</h2>

        <div className="landing-search">
          <SearchBar 
            filters={{ q, vertical } as any} 
            setFilters={(patch) => {
              if (patch.q !== undefined) {
                setQ(patch.q);
              }
            }} 
            onSearch={handleSearch}
          />
        </div>

        <div className="vertical-subbar" role="tablist" aria-label="Vertical selector">
          {verticalTabs.map((tab) => {
            const isActive = vertical === tab.key;
            const isDisabled = !tab.enabled;
            return (
              <button
                key={tab.key}
                className={`vertical-tab ${isActive ? "is-active" : ""}`}
                disabled={isDisabled}
                title={isDisabled ? "Coming soon" : undefined}
                onClick={() => setVertical(tab.key as Vertical)}
              >
                {tab.label}
                {isDisabled && <span>Coming soon</span>}
              </button>
            );
          })}
        </div>
      </section>

      <section className="featured-section">
        {loading ? (
          <div className="loading-state">Loading featured products...</div>
        ) : (
          <div className="featured-grid">
            <DataGrid items={featured} selectedId={null} onSelect={(id) => navigate(`/search?vertical=${vertical}&selected=${id}`)} />
          </div>
        )}
      </section>
    </div>
  );
}
