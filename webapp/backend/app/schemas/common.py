from __future__ import annotations

from typing import Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

T = TypeVar('T')


class ApiError(BaseModel):
    code: str
    message: str
    detail: dict[str, object] = Field(default_factory=dict)


class ApiResponse(BaseModel, Generic[T]):
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    status: str = 'ok'
    message: str = ''
    data: T | None = None
    error: ApiError | None = None


def ok(data: T, message: str = '') -> ApiResponse[T]:
    return ApiResponse(data=data, message=message)
