from fastapi import Header

from app.core.config import get_settings
from app.core.errors import ApiError, AppHTTPException


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if x_admin_token != settings.admin_token:
        raise AppHTTPException(status_code=401, error=ApiError(code="unauthorized", message="Invalid admin token"))
