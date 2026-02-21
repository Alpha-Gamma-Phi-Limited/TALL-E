from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meta import MetaOut
from app.services.meta import get_meta

Vertical = Literal["tech", "pharmaceuticals", "beauty", "home-appliances", "supplements", "pet-goods"]

router = APIRouter(prefix="/v2/meta", tags=["meta-v2"])


@router.get("", response_model=MetaOut)
def meta_v2(vertical: Vertical = Query(...), db: Session = Depends(get_db)) -> MetaOut:
    return get_meta(db, vertical=vertical)
