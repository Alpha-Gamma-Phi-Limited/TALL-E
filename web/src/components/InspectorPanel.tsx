import { Cross2Icon } from "@radix-ui/react-icons";

import { ProductDetail } from "../api/client";

type Props = {
  product: ProductDetail | null;
  loading: boolean;
  onClose: () => void;
};

const money = new Intl.NumberFormat("en-NZ", { style: "currency", currency: "NZD" });

export default function InspectorPanel({ product, loading, onClose }: Props) {
  if (!product && !loading) return null;

  return (
    <section className="product-overlay" role="dialog" aria-modal="true">
      <div className="product-sheet">
        <button className="close-sheet" onClick={onClose} aria-label="Close">
          <Cross2Icon />
        </button>

        {loading ? (
          <p>Loading product…</p>
        ) : (
          <div className="sheet-content">
            <div className="sheet-main">
              <div className="sheet-media-box">
                {product?.image_url ? (
                  <img src={product.image_url} alt={product.canonical_name} />
                ) : (
                  <div className="media-placeholder">NO IMAGE</div>
                )}
              </div>
              <div className="sheet-details">
                <p className="sheet-brand">{product?.brand}</p>
                <h2>{product?.canonical_name}</h2>
                <p className="sheet-subtitle">
                  {product?.category} ·{" "}
                  {product?.value_score !== null ? `Value score ${product?.value_score?.toFixed(2)}` : "Price-first comparison"}
                </p>
              </div>
            </div>

            <div className="sheet-columns">
              <div className="sheet-col">
                <h3>Specifications</h3>
                <ul className="spec-list">
                  {Object.entries(product?.attributes ?? {}).map(([key, value]) => (
                    <li key={key}>
                      <span className="spec-key">{key}</span>
                      <strong className="spec-val">{String(value)}</strong>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="sheet-col">
                <h3>Current Offers</h3>
                <ul className="offer-list">
                  {(product?.offers ?? []).map((offer) => (
                    <li key={offer.retailer_product_id} className="offer-item">
                      <div className="offer-info">
                        <span className="offer-retailer">{offer.retailer}</span>
                        <small className="offer-status">{offer.availability || "availability unknown"}</small>
                      </div>
                      <div className="offer-price">
                        <strong>{money.format(offer.promo_price_nzd ?? offer.price_nzd)}</strong>
                        {offer.promo_price_nzd && (
                          <small className="was-price">Was {money.format(offer.price_nzd)}</small>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
