export type Offer = {
  retailer: string;
  retailer_product_id: string;
  title: string;
  url: string;
  image_url: string | null;
  availability: string | null;
  price_nzd: number;
  promo_price_nzd: number | null;
  promo_text: string | null;
  discount_pct: number | null;
  captured_at: string;
};

export type ProductListItem = {
  id: string;
  canonical_name: string;
  vertical: string;
  brand: string;
  category: string;
  image_url: string | null;
  attributes: Record<string, unknown>;
  best_offer: Offer | null;
  offers_count: number;
  value_score: number | null;
};

export type ProductsResponse = {
  items: ProductListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type ProductDetail = {
  id: string;
  canonical_name: string;
  vertical: string;
  brand: string;
  category: string;
  model_number: string | null;
  gtin: string | null;
  mpn: string | null;
  image_url: string | null;
  attributes: Record<string, unknown>;
  offers: Offer[];
  value_score: number | null;
  history: Offer[] | null;
};

export type MetaResponse = {
  vertical: string | null;
  categories: string[];
  brands: string[];
  retailers: { slug: string; name: string }[];
  filters: Record<string, string[]>;
  scoring_config: Record<string, unknown>;
};

type ViteEnvImportMeta = ImportMeta & {
  env?: Record<string, string | undefined>;
};

const baseUrl = (import.meta as ViteEnvImportMeta).env?.VITE_API_BASE_URL ?? "http://localhost:8000";

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    sp.set(key, String(value));
  });
  return sp.toString();
};

export async function fetchProducts(params: Record<string, string | number | boolean | undefined | null>) {
  const response = await fetch(`${baseUrl}/v2/products?${qs(params)}`);
  if (!response.ok) throw new Error(`Failed to fetch products (${response.status})`);
  return (await response.json()) as ProductsResponse;
}

export async function fetchProductDetail(productId: string, vertical: string) {
  const response = await fetch(`${baseUrl}/v2/products/${productId}?${qs({ vertical })}`);
  if (!response.ok) throw new Error(`Failed to fetch product detail (${response.status})`);
  return (await response.json()) as ProductDetail;
}

export async function fetchMeta(vertical: string) {
  const response = await fetch(`${baseUrl}/v2/meta?${qs({ vertical })}`);
  if (!response.ok) throw new Error(`Failed to fetch meta (${response.status})`);
  return (await response.json()) as MetaResponse;
}
