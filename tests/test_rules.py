"""Тесты правило-движка (rules.py)."""
from models import Ad, Region, Target
from rules import matches as rules_matches


def ad(**kwargs) -> Ad:
    base = dict(
        ad_id="1",
        title="Коньки фигурные Graf Etude",
        price_byn=250.0,
        city="Гомель",
        params={
            "region": {"v": 2, "vl": "Гомельская область"},
            "area": {"v": "5", "vl": "Гомель"},
            "sports_shoes_size": {"v": [24], "vl": ["37"]},
            "condition": {"v": "1", "vl": "Б/у"},
        },
        images=[],
    )
    if "params" in kwargs:
        merged = dict(base["params"])
        merged.update(kwargs["params"])
        kwargs["params"] = merged
    base.update(kwargs)
    return Ad(**base)


def target(**kwargs) -> Target:
    base = dict(
        name="test",
        query="коньки",
        regions=[Region(rgn=2, ar=5, label="Гомель")],
        must_contain=["graf", "edea"],
        params={"sports_shoes_size": {"min": 37, "max": 37}},
    )
    base.update(kwargs)
    return Target(**base)


# --- ключевые слова ---

def test_keywords_or_match():
    t = target(must_contain=["graf", "edea"])
    assert rules_matches(t, ad(title="Коньки фигурные EDEA"))
    assert rules_matches(t, ad(title="Коньки фигурные Graf"))
    assert not rules_matches(t, ad(title="Коньки фигурные risport"))


def test_keywords_all_mode():
    t = target(must_contain=["graf", "фигурные"], all_keywords=True)
    assert rules_matches(t, ad(title="Коньки фигурные Graf"))
    assert not rules_matches(t, ad(title="Коньки Graf"))


def test_excludes():
    t = target(must_not_contain=["хоккейн", "детск"])
    assert rules_matches(t, ad(title="Коньки фигурные Graf 37"))
    assert not rules_matches(t, ad(title="Коньки хоккейные Graf 37"))
    assert not rules_matches(t, ad(title="Детские коньки Graf 37"))


# --- размер (параметры) ---

def test_param_range_single_size():
    t = target(params={"sports_shoes_size": {"min": 37, "max": 37}})
    assert rules_matches(t, ad())  # vl=["37"]
    assert not rules_matches(t, ad(params={"sports_shoes_size": {"v": [23], "vl": ["36"]}}))


def test_param_range_multiple_sizes_in_ad():
    """Объявление с несколькими размерами ('35,36,37,38') подходит, если один из них 37."""
    t = target(params={"sports_shoes_size": {"min": 37, "max": 37}})
    ad_multi = ad(params={"sports_shoes_size": {"v": [22, 23, 24], "vl": ["35", "36", "37", "38"]}})
    assert rules_matches(t, ad_multi)


def test_param_exact_list():
    t = target(params={"condition": ["1"]})
    assert rules_matches(t, ad())
    assert not rules_matches(t, ad(params={"condition": {"v": "2", "vl": "Новое"}}))


def test_param_missing_rejected():
    t = target(params={"sports_shoes_size": {"min": 37, "max": 37}})
    a = ad()
    a.params = {"region": {"v": 2}, "area": {"v": "5"}}  # без размера
    assert not rules_matches(t, a)


# --- цена ---

def test_price_range():
    t = target(price={"min": 100, "max": 300})
    assert rules_matches(t, ad(price_byn=250.0))
    assert not rules_matches(t, ad(price_byn=50.0))
    assert not rules_matches(t, ad(price_byn=400.0))


def test_price_missing_rejected():
    t = target(price={"max": 300})
    assert not rules_matches(t, ad(price_byn=None))


# --- город ---

def test_city_by_codes():
    gomel = target(regions=[Region(rgn=2, ar=5, label="Гомель")])
    assert rules_matches(gomel, ad())  # region=2, area=5

    minsk = target(regions=[Region(rgn=7, label="Минск")])
    ad_minsk = ad(params={
        "region": {"v": 7, "vl": "Минск"},
        "area": {"v": "24", "vl": "Первомайский"},
    })
    assert rules_matches(minsk, ad_minsk)
    assert not rules_matches(minsk, ad())  # Гомель не подходит для Минска


def test_city_no_regions_ok():
    t = target(regions=[])
    assert rules_matches(t, ad())
