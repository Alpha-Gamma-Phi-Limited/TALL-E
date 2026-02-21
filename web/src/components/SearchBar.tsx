import { MagnifyingGlassIcon } from "@radix-ui/react-icons";

import { ProductFilters } from "../hooks/useProductSearchParams";

type Props = {
  filters: Partial<ProductFilters>;
  setFilters: (patch: Partial<ProductFilters>) => void;
  onSearch?: (q: string) => void;
  autoFocus?: boolean;
};

export default function SearchBar({ filters, setFilters, onSearch, autoFocus }: Props) {
  const searchPlaceholder =
    filters.vertical === "pharmaceuticals"
      ? "Search by product name, ingredient, strength"
      : filters.vertical === "beauty"
        ? "Search by product name, brand, skin concern"
        : filters.vertical === "home-appliances"
          ? "Search by product name, model, brand"
          : filters.vertical === "supplements"
            ? "Search by product name, brand, category"
            : filters.vertical === "pet-goods"
              ? "Search by product name, pet type, brand"
            : "Search by product name, model, GTIN";

  return (
    <div className="search-control">
      <MagnifyingGlassIcon width={18} height={18} />
      <input
        value={filters.q}
        onChange={(e) => setFilters({ q: e.target.value })}
        onKeyDown={(e) => {
          if (e.key === "Enter" && onSearch) {
            onSearch(filters.q ?? "");
          }
        }}
        placeholder={searchPlaceholder}
        aria-label="Search products"
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus={autoFocus}
      />
    </div>
  );
}
