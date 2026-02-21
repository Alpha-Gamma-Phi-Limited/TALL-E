from pydantic import BaseModel


class MetaOut(BaseModel):
    vertical: str | None = None
    categories: list[str]
    brands: list[str]
    retailers: list[dict[str, str]]
    filters: dict[str, list[str]]
    scoring_config: dict[str, object]
