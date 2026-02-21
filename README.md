# WorthIt (TALL-E)

Multi-vertical price intelligence platform for NZ retail, currently supporting technology, pharmacy, and beauty.

## Stack

- API: FastAPI + SQLAlchemy + Alembic
- Worker: Python ingestion pipeline + matching engine
- Web: React + Vite + TypeScript + Radix UI
- Data: PostgreSQL + Redis
- Infra: Docker Compose

## Repository Layout

- `api/`: backend API, models, migrations, tests
- `worker/`: ingestion adapters, matching engine, pipeline, fixtures, tests
- `web/`: 3-pane UI workspace (filter rail, data grid, inspector)
- `shared/verticals/tech/`: taxonomy, attributes, value scoring config
- `shared/verticals/pharma/`: taxonomy, attributes, vertical config
- `infra/`: docker-compose for local stack

## Quick Start

### Option A: Docker Compose

```bash
cd infra
docker compose up --build
```

API will be available at `http://localhost:8000` and web at `http://localhost:5173`.

To include worker services:

```bash
cd infra
docker compose --profile workers up --build
```

### Option B: Local Processes

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r api/requirements.txt
pip install -r worker/requirements.txt
cd web && npm install && cd ..
```

## API Endpoints

- `GET /v1/products`
- `GET /v1/products/{id}`
- `GET /v1/meta`
- `GET /v2/products?vertical=tech|pharma|beauty`
- `GET /v2/products/{id}?vertical=tech|pharma|beauty`
- `GET /v2/meta?vertical=tech|pharma|beauty`
- `POST /v1/admin/reconcile` (requires `X-Admin-Token`)
- `GET /v1/admin/ingestion-runs` (requires `X-Admin-Token`)
- `GET /health`

## Local Development

### API

```bash
cd api
uvicorn app.main:app --reload --port 8000
```

### Worker (fixture mode)

```bash
cd worker
python -m worker.main --retailer pb-tech --mode fixture
```

### Worker (live mode)

```bash
cd worker
python -m worker.main --retailer pb-tech --mode live --max-products 120
```

Retailer options:

- `pb-tech`
- `jb-hi-fi`
- `noel-leeming`
- `harvey-norman`
- `chemist-warehouse`
- `bargain-chemist`
- `life-pharmacy`
- `mecca`
- `sephora`
- `farmers-beauty`

### Web

```bash
cd web
npm run dev
```

Set API base URL when needed:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Make Targets

```bash
make test
make run-api
make run-web
make worker-pb
```

## Database Notes

Core tables:

- `products`
- `retailer_products`
- `prices`
- `latest_prices`
- `ingestion_runs`
- `retailers`
- `product_overrides`

Initial Alembic migration lives in `api/alembic/versions/0001_initial.py`.

## Matching Priority

1. GTIN
2. MPN/model number
3. Manual override
4. Fuzzy match (brand/category constrained + attribute overlap)

## Caching

Redis cache keys:

- `products:{hash}:page:{n}:v:{version}`
- `product:{id}:v:{version}`
- `meta:{vertical}:v:{version}`

Configured via `WORTHIT_CACHE_SCHEMA_VERSION`.

## Tests

```bash
pytest
```

## Environment Variables

- `WORTHIT_DATABASE_URL`
- `WORTHIT_REDIS_URL`
- `WORTHIT_ADMIN_TOKEN`
- `WORTHIT_CACHE_SCHEMA_VERSION`

See `infra/.env.example`.
