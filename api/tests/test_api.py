def test_products_list(client):
    response = client.get("/v1/products", params={"q": "acer", "sort": "price_asc"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["best_offer"]["retailer"] in {"pb-tech", "jb-hi-fi"}
    assert payload["items"][0]["offers_count"] == 2
    assert payload["items"][0]["vertical"] == "tech"


def test_product_detail_not_found(client):
    response = client.get("/v1/products/missing")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_meta(client):
    response = client.get("/v1/meta")
    assert response.status_code == 200
    payload = response.json()
    assert "laptops" in payload["categories"]
    assert any(retailer["slug"] == "pb-tech" for retailer in payload["retailers"])


def test_products_v2_requires_vertical(client):
    response = client.get("/v2/products")
    assert response.status_code == 422


def test_products_v2_tech_scope(client):
    response = client.get("/v2/products", params={"vertical": "tech", "q": "acer"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["vertical"] == "tech"


def test_products_v2_pharma_scope(client):
    response = client.get("/v2/products", params={"vertical": "pharma", "q": "panadol"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["vertical"] == "pharma"
    assert payload["items"][0]["value_score"] is None


def test_products_v2_beauty_scope(client):
    response = client.get("/v2/products", params={"vertical": "beauty", "q": "niacinamide"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["vertical"] == "beauty"
    assert payload["items"][0]["best_offer"]["retailer"] in {"mecca", "sephora", "farmers-beauty"}
    assert payload["items"][0]["value_score"] is None


def test_meta_v2_scoped(client):
    response = client.get("/v2/meta", params={"vertical": "pharma"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["vertical"] == "pharma"
    assert any(retailer["slug"] == "chemist-warehouse" for retailer in payload["retailers"])


def test_meta_v2_beauty_scope(client):
    response = client.get("/v2/meta", params={"vertical": "beauty"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["vertical"] == "beauty"
    assert any(retailer["slug"] == "mecca" for retailer in payload["retailers"])


def test_product_detail_v2_vertical_guard(client):
    tech_product = client.get("/v2/products", params={"vertical": "tech", "q": "acer"}).json()["items"][0]
    response = client.get(f"/v2/products/{tech_product['id']}", params={"vertical": "pharma"})
    assert response.status_code == 404


def test_admin_requires_token(client):
    response = client.get("/v1/admin/ingestion-runs")
    assert response.status_code == 401


def test_admin_ingestion_runs(client):
    response = client.get("/v1/admin/ingestion-runs", headers={"X-Admin-Token": "dev-admin-token"})
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["status"] == "completed"
