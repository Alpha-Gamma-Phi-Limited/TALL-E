import { KeyboardEvent } from "react";

import { ProductListItem } from "../api/client";

type Props = {
  items: ProductListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
};

const money = new Intl.NumberFormat("en-NZ", { style: "currency", currency: "NZD" });

export default function DataGrid({ items, selectedId, onSelect }: Props) {
  if (items.length === 0) {
    return <div className="empty-cards">No products match your filters.</div>;
  }

  const verticalPlaceholder = (vertical: string) => {
    if (vertical === "pharmaceuticals") return "PHARMACEUTICALS";
    if (vertical === "home-appliances") return "HOME";
    if (vertical === "supplements") return "SUPPLEMENTS";
    if (vertical === "pet-goods") return "PET GOODS";
    if (vertical === "beauty") return "BEAUTY";
    return "TECH";
  };

  const handleCardKeyDown = (event: KeyboardEvent<HTMLElement>, id: string) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    onSelect(id);
  };

  return (
    <div className="card-grid">
      {items.map((item) => {
        const offer = item.best_offer;
        const effective = offer?.promo_price_nzd ?? offer?.price_nzd ?? null;
        return (
          <article
            key={item.id}
            className={`product-card ${selectedId === item.id ? "selected" : ""}`}
            onClick={() => onSelect(item.id)}
            onKeyDown={(event) => handleCardKeyDown(event, item.id)}
            role="button"
            tabIndex={0}
            aria-pressed={selectedId === item.id}
          >
            <div className="card-media">
              {item.image_url ? (
                <img src={item.image_url} alt={item.canonical_name} loading="lazy" />
              ) : (
                <div className="media-placeholder">{verticalPlaceholder(item.vertical)}</div>
              )}
            </div>

            <div className="card-body">
              <span className="card-brand">{item.brand}</span>
              <h3>{item.canonical_name}</h3>
              <p className="card-category">{item.category}</p>
            </div>

            <div className="card-foot">
              <div className="price-box">
                <strong>{effective ? money.format(effective) : "Price unavailable"}</strong>
                {offer?.promo_price_nzd && (
                  <span className="was-price-tag">Was {money.format(offer.price_nzd)}</span>
                )}
              </div>
              <div className="offer-meta">
                <span className="retailer-name">{offer?.retailer ?? "No current offer"}</span>
                <span className="value-tag">
                  {item.value_score !== null ? `Score: ${item.value_score.toFixed(1)}` : "Unranked"}
                </span>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
