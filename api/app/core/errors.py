from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException


@dataclass
class ApiError:
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class AppHTTPException(HTTPException):
    def __init__(self, status_code: int, error: ApiError):
        super().__init__(status_code=status_code, detail=error.to_dict())
