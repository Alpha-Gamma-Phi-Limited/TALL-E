from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin_token
from app.db.session import get_db
from app.schemas.admin import IngestionRunOut, ReconcileRequest, ReconcileResponse
from app.services.admin import list_ingestion_runs, reconcile_product

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin_token)])


@router.post("/reconcile", response_model=ReconcileResponse)
def reconcile(payload: ReconcileRequest, db: Session = Depends(get_db)) -> ReconcileResponse:
    return reconcile_product(db, payload)


@router.get("/ingestion-runs", response_model=list[IngestionRunOut])
def ingestion_runs(limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)) -> list[IngestionRunOut]:
    return list_ingestion_runs(db, limit=limit)
