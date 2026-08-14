from __future__ import annotations

from pydantic import BaseModel


class SupportedCityRead(BaseModel):
    name: str
    province: str
    city_code: str
    tier: str
    verified: bool = False
