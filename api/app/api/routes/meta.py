from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meta import MetaOut
from app.services.meta import get_meta

router = APIRouter(prefix="/v1/meta", tags=["meta"])


@router.get("", response_model=MetaOut)
def meta(db: Session = Depends(get_db)) -> MetaOut:
    return get_meta(db)
