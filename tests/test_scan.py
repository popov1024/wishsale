"""Тесты scan_once: дедупликация, force и limit."""
from main import scan_once
from models import Ad, Target
from store import Store


class FakeFetcher:
    def __init__(self, ads):
        self.ads = ads

    def fetch(self, target):
        return self.ads


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def send_ad(self, chat_id, target_name, ad, thread_id=None):
        self.sent.append((chat_id, thread_id, ad.key))
        return True


def make_ad(ad_id="1", **kw) -> Ad:
    base = dict(ad_id=ad_id, title="Коньки Graf", price_byn=250.0, city="Гомель", params={}, images=[])
    base.update(kw)
    return Ad(**base)


def make_target(**kw) -> Target:
    base = dict(name="test", query="коньки")
    base.update(kw)
    return Target(**base)


def test_first_scan_sends_all(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    ads = [make_ad("1"), make_ad("2")]
    n = scan_once(FakeFetcher(ads), store, FakeNotifier(), [make_target()], [(111, None)])
    assert n == 2


def test_second_scan_is_deduped(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    notifier = FakeNotifier()
    ads = [make_ad("1"), make_ad("2")]
    scan_once(FakeFetcher(ads), store, notifier, [make_target()], [(111, None)])
    n = scan_once(FakeFetcher(ads), store, notifier, [make_target()], [(111, None)])
    assert n == 0


def test_force_resends_seen_ads(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    notifier = FakeNotifier()
    ads = [make_ad("1"), make_ad("2")]
    scan_once(FakeFetcher(ads), store, notifier, [make_target()], [(111, None)])
    notifier.sent.clear()
    n = scan_once(FakeFetcher(ads), store, notifier, [make_target()], [(111, None)], force=True)
    assert n == 2


def test_limit_caps_notifications(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    notifier = FakeNotifier()
    ads = [make_ad(str(i)) for i in range(10)]
    n = scan_once(FakeFetcher(ads), store, notifier, [make_target()], [(111, None)], limit=3)
    assert n == 3
    assert len(notifier.sent) == 3
