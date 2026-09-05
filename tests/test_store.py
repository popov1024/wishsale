"""Тесты хранилища (store.py)."""
from store import Store
from models import Ad


def make_store(tmp_path):
    return Store(str(tmp_path / "test.db"))


def ad(ad_id="1", **kw) -> Ad:
    base = dict(ad_id=ad_id, title="Коньки Graf", price_byn=250.0, city="Гомель", params={}, images=[])
    base.update(kw)
    return Ad(**base)


def test_dedup(tmp_path):
    s = make_store(tmp_path)
    a = ad()
    assert s.is_new(a.key)
    s.mark_seen(a, notified=True)
    assert not s.is_new(a.key)
    # повторная пометка не ломает notified_at
    s.mark_seen(a, notified=False)
    row = s.conn.execute("SELECT notified_at FROM seen_ads WHERE key=?", (a.key,)).fetchone()
    assert row["notified_at"] is not None


def test_app_state(tmp_path):
    s = make_store(tmp_path)
    s.set_state("last_scan", "2026-01-01")
    assert s.get_state("last_scan") == "2026-01-01"
