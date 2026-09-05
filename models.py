"""Единые модели данных: объявление (Ad) и объект мониторинга (Target)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Ad:
    """Единая модель объявления с любой площадки."""

    ad_id: str
    source: str = "kufar"
    url: str = ""
    title: str = ""
    price_byn: Optional[float] = None
    city: str = ""
    # код параметра -> {"v": исходное значение, "vl": текст для показа}
    params: dict[str, dict[str, Any]] = field(default_factory=dict)
    images: list[str] = field(default_factory=list)
    published_at: Optional[str] = None

    @property
    def key(self) -> str:
        return f"{self.source}:{self.ad_id}"

    def param_label(self, code: str) -> str:
        """Человекочитаемое значение параметра (для сообщения)."""
        entry = self.params.get(code)
        if not entry:
            return ""
        vl = entry.get("vl")
        if isinstance(vl, list):
            return ", ".join(str(x) for x in vl)
        return str(vl) if vl is not None else ""


@dataclass
class Region:
    rgn: int
    ar: Optional[int] = None
    label: str = ""


@dataclass
class Target:
    """Что мониторим: поисковый запрос + регионы + фильтры."""

    name: str
    query: str
    regions: list[Region] = field(default_factory=list)
    category: Optional[str] = None
    must_contain: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    # код параметра -> [значения] (точное совпадение) или {min, max} (диапазон)
    params: dict[str, Any] = field(default_factory=dict)
    price: Optional[dict[str, float]] = None  # {min, max} в BYN
    all_keywords: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "Target":
        regions = [Region(**r) for r in data.get("regions", [])]
        return cls(
            name=data["name"],
            query=data.get("query", ""),
            regions=regions,
            category=str(data["category"]) if data.get("category") else None,
            must_contain=[str(w) for w in data.get("must_contain", [])],
            must_not_contain=[str(w) for w in data.get("must_not_contain", [])],
            params=dict(data.get("params", {})),
            price=dict(data["price"]) if data.get("price") else None,
            all_keywords=bool(data.get("all_keywords", False)),
        )
