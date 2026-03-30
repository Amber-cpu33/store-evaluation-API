# -*- coding: utf-8 -*-
from data import loader


def get_city_list() -> list[str]:
    return sorted(loader.geo_tree.keys())


def get_district_list(city: str) -> list[str]:
    districts = list(loader.geo_tree.get(city, {}).keys())
    return sorted(
        districts,
        key=lambda d: loader.district_lookup.get((city, d), {}).get('行政區人口', 0),
        reverse=True
    )


def get_neighborhood_list(city: str, district: str) -> list[str]:
    return loader.geo_tree.get(city, {}).get(district, [])


def check_valid_geo(city: str, district: str, neighborhood: str) -> bool:
    return neighborhood in loader.geo_tree.get(city, {}).get(district, [])
