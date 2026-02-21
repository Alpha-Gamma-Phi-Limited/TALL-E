from pydantic import BaseModel


class ReconcileRequest(BaseModel):
    retailer_product_id: str
    product_id: str
    reason: str | None = None


class ReconcileResponse(BaseModel):
    status: str
    retailer_product_id: str
    product_id: str


class IngestionRunOut(BaseModel):
    id: str
    retailer: str
    status: str
    items_total: int
    items_new: int
    items_updated: int
    items_failed: int
    started_at: str
    finished_at: str | None
