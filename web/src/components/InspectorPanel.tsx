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
          <>
            <p className="sheet-brand">{product?.brand}</p>
            <h2>{product?.canonical_name}</h2>
            <p className="sheet-subtitle">
              {product?.category} ·{" "}
              {product?.value_score !== null ? `Value score ${product?.value_score?.toFixed(2)}` : "Price-first comparison"}
            </p>

            <div className="sheet-columns">
              <div>
                <h3>Specifications</h3>
                <ul>
                  {Object.entries(product?.attributes ?? {}).map(([key, value]) => (
                    <li key={key}>
                      <span>{key}</span>
                      <strong>{String(value)}</strong>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h3>Offers</h3>
                <ul>
                  {(product?.offers ?? []).map((offer) => (
                    <li key={offer.retailer_product_id}>
                      <div>
                        <span>{offer.retailer}</span>
                        <small>{offer.availability || "availability unknown"}</small>
                      </div>
                      <strong>{money.format(offer.promo_price_nzd ?? offer.price_nzd)}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
