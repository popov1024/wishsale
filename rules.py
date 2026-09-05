"""Правило-движок: проверяет объявление против фильтров таргета."""
from __future__ import annotations

from typing import Any, Optional

from models import Ad, Target
from utils import to_float


def matches(target: Target, ad: Ad) -> bool:
    """True, если объявление подходит под все фильтры таргета."""
    return (
        _matches_price(target, ad)
        and _matches_keywords(target, ad)
        and _matches_excludes(target, ad)
        and _matches_params(target, ad)
        and _matches_city(target, ad)
    )


def _matches_price(target: Target, ad: Ad) -> bool:
    if not target.price:
        return True
    if ad.price_byn is None:
        return False
    lo = target.price.get("min")
    hi = target.price.get("max")
    if lo is not None and ad.price_byn < float(lo):
        return False
    if hi is not None and ad.price_byn > float(hi):
        return False
    return True


def _matches_keywords(target: Target, ad: Ad) -> bool:
    if not target.must_contain:
        return True
    title = ad.title.lower()
    words = [w.lower() for w in target.must_contain]
    if target.all_keywords:
        return all(w in title for w in words)
    return any(w in title for w in words)


def _matches_excludes(target: Target, ad: Ad) -> bool:
    if not target.must_not_contain:
        return True
    title = ad.title.lower()
    return not any(w.lower() in title for w in target.must_not_contain)


def _matches_params(target: Target, ad: Ad) -> bool:
    for code, rule in target.params.items():
        entry = ad.params.get(code)
        if not entry:
            return False
        if not _entry_matches(entry, rule):
            return False
    return True


def _entry_matches(entry: dict[str, Any], rule: Any) -> bool:
    """Сверяет параметр объявления ({v, vl}) с правилом.

    rule: [значения] — точное совпадение строк;
    rule: {min, max} — числовой диапазон (по всем представлениям размера).
    """
    candidates: list[Any] = []
    for key in ("vl", "v"):
        val = entry.get(key)
        if isinstance(val, list):
            candidates.extend(val)
        elif val is not None:
            candidates.append(val)

    if isinstance(rule, (list, tuple, set)):
        allowed = {str(x).strip().lower() for x in rule}
        return any(str(c).strip().lower() in allowed for c in candidates)

    if isinstance(rule, dict):
        nums = [to_float(c) for c in candidates]
        nums = [n for n in nums if n is not None]
        if not nums:
            return False
        lo = rule.get("min")
        hi = rule.get("max")
        return any(
            (lo is None or n >= float(lo)) and (hi is None or n <= float(hi))
            for n in nums
        )
    return False


def _matches_city(target: Target, ad: Ad) -> bool:
    """Сверяет регион/город объявления с регионами таргета по кодам.

    Для Минска area — это район (Московский, Центральный...), поэтому
    сравниваем коды region/area из ad_parameters, а не текст.
    """
    if not target.regions:
        return True
    region_code = ad.params.get("region", {}).get("v")
    area_code = ad.params.get("area", {}).get("v")
    for r in target.regions:
        if str(r.rgn) == str(region_code) and (
            r.ar is None or str(r.ar) == str(area_code)
        ):
            return True
    return False
