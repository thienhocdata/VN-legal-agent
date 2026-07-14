from __future__ import annotations

import unicodedata


HCM_ALIASES = {
    "tp ho chi minh", "thanh pho ho chi minh", "ho chi minh", "tphcm", "hcm", "sai gon", "saigon"
}


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower().strip())
    return "".join(c for c in value if unicodedata.category(c) != "Mn").replace("đ", "d")


def normalize_locality(value: str | None) -> tuple[str | None, bool]:
    if not value:
        return None, False
    if _plain(value).replace(".", "") in HCM_ALIASES:
        return "TP. Hồ Chí Minh", True
    return value.strip(), False


def coverage_view() -> dict:
    return {
        "primary_locality": "TP. Hồ Chí Minh",
        "operating_address": "85 Hưng Nhơn, Thành phố Hồ Chí Minh",
        "supported_workflow": "preliminary individual/household land-use-right transfer preparation",
        "neighboring_provinces": "national-law analysis only unless a separate reviewed locality source pack is installed",
        "local_sources": ["3279/QĐ-UBND (partially effective)", "1351/QĐ-UBND (effective 2025-09-09)"],
    }
