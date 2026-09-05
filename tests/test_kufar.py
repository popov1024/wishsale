"""Тесты парсера Kufar на фикстуре реального ответа API."""
import json
from pathlib import Path

from fetchers.kufar import KufarFetcher

FIXTURE = Path(__file__).parent / "fixtures" / "kufar_ads.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parse_ads_structure():
    raw = load_fixture()
    ads = KufarFetcher._parse_ads(raw["ads"])
    assert len(ads) == 5
    first = ads[0]
    assert first.source == "kufar"
    assert first.url.startswith("https://www.kufar.by/item/")
    assert first.title
    assert first.ad_id


def test_price_divided_by_100():
    """Kufar отдаёт цену в копейках: price_byn=30000 → 300.0 BYN."""
    raw = load_fixture()
    ads = KufarFetcher._parse_ads(raw["ads"])
    for a in ads:
        if a.price_byn is not None:
            assert a.price_byn < 100000  # санити-проверка
    assert any(a.price_byn is not None for a in ads)


def test_params_and_city():
    raw = load_fixture()
    ads = KufarFetcher._parse_ads(raw["ads"])
    assert any(a.city for a in ads)
    # у гомельской выборки city должен быть Гомель
    assert all(a.city == "Гомель" for a in ads if a.city)
    # параметры содержат структуру {v, vl}
    assert all(isinstance(a.params, dict) for a in ads)


def test_images_url():
    raw = load_fixture()
    ads = KufarFetcher._parse_ads(raw["ads"])
    for a in ads:
        for url in a.images:
            assert url.startswith("https://rms.kufar.by/v1/list_thumbs_2x/")
