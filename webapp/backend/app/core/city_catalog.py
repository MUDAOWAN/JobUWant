from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupportedCity:
    name: str
    province: str
    city_code: str
    tier: str
    verified: bool = False
    aliases: tuple[str, ...] = ()


SUPPORTED_CITIES: tuple[SupportedCity, ...] = (
    SupportedCity('北京', '北京', '101010100', 'first'),
    SupportedCity('上海', '上海', '101020100', 'first'),
    SupportedCity('广州', '广东', '101280100', 'first', verified=True),
    SupportedCity('深圳', '广东', '101280600', 'first', verified=True),
    SupportedCity('成都', '四川', '101270100', 'new_first'),
    SupportedCity('重庆', '重庆', '101040100', 'new_first'),
    SupportedCity('杭州', '浙江', '101210100', 'new_first', verified=True),
    SupportedCity('武汉', '湖北', '101200100', 'new_first'),
    SupportedCity('苏州', '江苏', '101190400', 'new_first'),
    SupportedCity('西安', '陕西', '101110100', 'new_first'),
    SupportedCity('南京', '江苏', '101190100', 'new_first'),
    SupportedCity('长沙', '湖南', '101250100', 'new_first'),
    SupportedCity('天津', '天津', '101030100', 'new_first'),
    SupportedCity('郑州', '河南', '101180100', 'new_first'),
    SupportedCity('东莞', '广东', '101281600', 'new_first'),
    SupportedCity('青岛', '山东', '101120200', 'new_first'),
    SupportedCity('昆明', '云南', '101290100', 'new_first'),
    SupportedCity('宁波', '浙江', '101210400', 'new_first'),
    SupportedCity('合肥', '安徽', '101220100', 'new_first'),
    SupportedCity('佛山', '广东', '101280800', 'new_first'),
    SupportedCity('沈阳', '辽宁', '101070100', 'second'),
    SupportedCity('济南', '山东', '101120100', 'second'),
    SupportedCity('无锡', '江苏', '101190200', 'second'),
    SupportedCity('厦门', '福建', '101230200', 'second'),
    SupportedCity('福州', '福建', '101230100', 'second'),
    SupportedCity('温州', '浙江', '101210700', 'second'),
    SupportedCity('金华', '浙江', '101210900', 'second'),
    SupportedCity('哈尔滨', '黑龙江', '101050100', 'second'),
    SupportedCity('大连', '辽宁', '101070200', 'second'),
    SupportedCity('贵阳', '贵州', '101260100', 'second'),
    SupportedCity('南宁', '广西', '101300100', 'second'),
    SupportedCity('泉州', '福建', '101230500', 'second'),
    SupportedCity('石家庄', '河北', '101090100', 'second'),
    SupportedCity('长春', '吉林', '101060100', 'second'),
    SupportedCity('南昌', '江西', '101240100', 'second'),
    SupportedCity('惠州', '广东', '101280300', 'second'),
    SupportedCity('常州', '江苏', '101191100', 'second'),
    SupportedCity('嘉兴', '浙江', '101210300', 'second'),
    SupportedCity('徐州', '江苏', '101190800', 'second'),
    SupportedCity('南通', '江苏', '101190500', 'second'),
    SupportedCity('太原', '山西', '101100100', 'second'),
    SupportedCity('珠海', '广东', '101280700', 'second'),
    SupportedCity('中山', '广东', '101281700', 'second'),
    SupportedCity('绍兴', '浙江', '101210500', 'second'),
    SupportedCity('台州', '浙江', '101211000', 'second'),
    SupportedCity('烟台', '山东', '101120500', 'second'),
    SupportedCity('廊坊', '河北', '101090600', 'second'),
    SupportedCity('呼和浩特', '内蒙古', '101080100', 'second'),
    SupportedCity('兰州', '甘肃', '101160100', 'second'),
    SupportedCity('乌鲁木齐', '新疆', '101130100', 'second'),
    SupportedCity('海口', '海南', '101310100', 'second'),
    SupportedCity('银川', '宁夏', '101170100', 'second'),
    SupportedCity('西宁', '青海', '101150100', 'second'),
)


def list_supported_cities() -> list[SupportedCity]:
    return list(SUPPORTED_CITIES)


def resolve_city(city: str, city_code: str = '') -> SupportedCity:
    normalized_city = normalize_city_name(city)
    normalized_code = city_code.strip()
    if normalized_city:
        for item in SUPPORTED_CITIES:
            names = (item.name, f'{item.name}市', *item.aliases)
            if normalized_city in names:
                if normalized_code and normalized_code != item.city_code:
                    raise ValueError(f'city_code does not match city: {city}')
                return item
    if normalized_code:
        for item in SUPPORTED_CITIES:
            if normalized_code == item.city_code:
                return item
    raise ValueError(f'unsupported city: {city}')


def normalize_city_name(city: str) -> str:
    value = city.strip()
    if len(value) > 2 and value.endswith('市'):
        return value[:-1]
    return value

