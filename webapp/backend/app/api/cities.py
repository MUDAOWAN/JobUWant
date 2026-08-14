from __future__ import annotations

from fastapi import APIRouter

from app.core.city_catalog import list_supported_cities
from app.schemas.cities import SupportedCityRead
from app.schemas.common import ApiResponse, ok

router = APIRouter(prefix='/api/cities', tags=['cities'])


@router.get('', response_model=ApiResponse[list[SupportedCityRead]])
def get_cities() -> ApiResponse[list[SupportedCityRead]]:
    return ok(
        [
            SupportedCityRead(
                name=city.name,
                province=city.province,
                city_code=city.city_code,
                tier=city.tier,
                verified=city.verified,
            )
            for city in list_supported_cities()
        ]
    )
