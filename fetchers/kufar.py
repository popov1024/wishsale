"""Фетчер Kufar: REST-запросы к API, разбор JSON → единая модель Ad."""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from models import Ad, Region, Target

API_URL = "https://api.kufar.by/search-api/v2/search/rendered-paginated"
IMAGE_BASE = "https://rms.kufar.by/v1/list_thumbs_2x"

log = logging.getLogger(__name__)


class KufarFetcher:
    def __init__(
        self,
        user_agent: str,
        page_size: int = 30,
        max_pages: int = 2,
        session: Optional[requests.Session] = None,
    ):
        self.page_size = page_size
        self.max_pages = max_pages
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Origin": "https://www.kufar.by",
                "Accept": "application/json",
            }
        )

    def fetch(self, target: Target) -> list[Ad]:
        """Собирает объявления по всем регионам таргета."""
        ads: list[Ad] = []
        regions = target.regions or [Region(rgn=0)]
        for region in regions:
            try:
                ads.extend(self._fetch_region(target, region))
            except requests.RequestException as exc:
                log.warning("region %s: request failed: %s", region.label, exc)
            time.sleep(0.5)  # вежливая пауза между регионами
        return ads

    def _fetch_region(self, target: Target, region: Region) -> list[Ad]:
        results: list[Ad] = []
        cursor: Optional[str] = None
        page = 1
        while True:
            params = {
                "query": target.query,
                "size": self.page_size,
                "lang": "ru",
            }
            if target.category:
                params["cat"] = target.category
            if region.rgn:
                params["rgn"] = region.rgn
            if region.ar is not None:
                params["ar"] = region.ar
            if cursor:
                params["cursor"] = cursor

            resp = self.session.get(API_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            ads = data.get("ads") or []
            results.extend(self._parse_ads(ads))

            total = data.get("total") or 0
            if not ads or len(results) >= total or page >= self.max_pages:
                break
            # Kufar листается курсором: берём токен следующей страницы из ответа
            cursor = None
            for p in (data.get("pagination") or {}).get("pages") or []:
                if p.get("label") == "next" and p.get("token"):
                    cursor = p["token"]
                    break
            if not cursor:
                break
            page += 1
        return results

    @staticmethod
    def _parse_ads(raw_ads: list[dict]) -> list[Ad]:
        parsed: list[Ad] = []
        for a in raw_ads:
            params: dict = {}
            city = ""
            for p in a.get("ad_parameters") or []:
                code = p.get("p", "")
                params[code] = {"v": p.get("v"), "vl": p.get("vl")}
                if code == "area":
                    city = str(p.get("vl", ""))

            images = [
                f"{IMAGE_BASE}/{path}"
                for path in (im.get("path") for im in a.get("images") or [])
                if path
            ]

            price_byn = a.get("price_byn")
            parsed.append(
                Ad(
                    ad_id=str(a.get("ad_id", "")),
                    source="kufar",
                    url=a.get("ad_link", ""),
                    title=a.get("subject", ""),
                    # Kufar отдаёт цену в копейках
                    price_byn=(float(price_byn) / 100.0) if price_byn else None,
                    city=city,
                    params=params,
                    images=images,
                    published_at=a.get("list_time"),
                )
            )
        return parsed
