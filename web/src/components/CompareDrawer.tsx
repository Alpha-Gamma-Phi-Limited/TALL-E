import * as Dialog from "@radix-ui/react-dialog";

import { ProductListItem } from "../api/client";

type Props = {
  products: ProductListItem[];
};

const money = new Intl.NumberFormat("en-NZ", { style: "currency", currency: "NZD" });

export default function CompareDrawer({ products }: Props) {
  return (
    <Dialog.Root>
      <Dialog.Trigger className="compare-trigger">Compare top {products.length}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="compare-overlay" />
        <Dialog.Content className="compare-content">
          <Dialog.Title>Quick Comparison</Dialog.Title>
          <p className="compare-subtitle">Snapshot of the current top products in the result set.</p>
          <div className="compare-grid">
            {products.slice(0, 4).map((product) => {
              const best = product.best_offer;
              return (
                <article key={product.id}>
                  <h3>{product.canonical_name}</h3>
                  <p>{product.brand}</p>
                  <p>{best ? money.format(best.promo_price_nzd ?? best.price_nzd) : "No offer"}</p>
                  <span>Value {product.value_score !== null ? product.value_score.toFixed(2) : "n/a"}</span>
                </article>
              );
            })}
          </div>
          <Dialog.Close className="compare-close">Close</Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
