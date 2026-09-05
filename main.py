"""Точка входа: мониторинг Kufar + уведомления в фиксированный чат Telegram.

Запуск:
    python main.py                 # цикл сканирования и рассылка
    python main.py --once          # один цикл сканирования и выход (для проверки)
    python main.py --once --force --limit 3   # тест: повторно отправить до 3 объявлений

Получатели задаются в .env через NOTIFY_CHAT_ID: число (личный чат, группа),
@username канала или формат chat_id:thread_id (топик форума/супергруппы).
Можно несколько через запятую.
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

from fetchers.kufar import KufarFetcher
from models import Target
from notifier import Notifier
from rules import matches
from store import Store

log = logging.getLogger(__name__)


def setup_logging(log_dir: str) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(log_dir) / "wishsale.log", encoding="utf-8"),
        ],
    )


def load_config_targets(cfg: dict) -> list[Target]:
    return [Target.from_dict(t) for t in cfg.get("targets", [])]


def parse_recipients(raw: str) -> list[tuple[int | str, int | None]]:
    """Парсит NOTIFY_CHAT_ID.

    '123:5, @chan, -1009:7' → [(123, 5), ('@chan', None), (-1009, 7)]
    Числовой chat_id приводится к int, @username остаётся строкой;
    thread id после ':' — id топика в форуме/супергруппе (опционально).
    """
    recipients = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        chat_id, _, thread_id = token.partition(":")
        chat_id = chat_id.strip()
        thread_id = thread_id.strip()
        if chat_id.lstrip("-").isdigit():
            chat_id = int(chat_id)
        recipients.append((chat_id, int(thread_id) if thread_id else None))
    return recipients


def scan_once(
    fetcher,
    store,
    notifier,
    targets: list[Target],
    recipients: list,
    force: bool = False,
    limit: int = 0,
) -> int:
    """Один цикл сканирования. Возвращает число отправленных объявлений.

    force — игнорировать дедупликацию (отправить заново всё подходящее);
    limit — максимум объявлений для отправки (0 — без ограничения).
    """
    sent = 0
    for target in targets:
        if limit and sent >= limit:
            break
        try:
            ads = fetcher.fetch(target)
        except Exception:
            log.exception("target '%s': fetch failed", target.name)
            continue

        new_count = 0
        for ad in ads:
            if limit and sent >= limit:
                break
            if not matches(target, ad):
                continue
            if force or store.is_new(ad.key):
                delivered = 0
                for chat_id, thread_id in recipients:
                    if notifier.send_ad(chat_id, target.name, ad, thread_id=thread_id):
                        delivered += 1
                store.mark_seen(ad, notified=delivered > 0)
                new_count += 1
                sent += 1
                log.info(
                    "new ad: %s | %s | %.2f BYN | %s | %d recipient(s)",
                    ad.title, ad.city, ad.price_byn or 0, ad.url, delivered,
                )
            else:
                store.mark_seen(ad, notified=False)
        log.info("target '%s': %d ads, %d new", target.name, len(ads), new_count)
    store.set_state("last_scan", time.strftime("%Y-%m-%d %H:%M:%S"))
    return sent


def build_runtime(cfg: dict, token: str):
    """Фетчер, нотификатор и таргеты из config.yaml."""
    app_cfg = cfg.get("app", {})
    fetcher = KufarFetcher(
        user_agent=app_cfg.get("user_agent", "wishsale/0.1"),
        page_size=int(app_cfg.get("page_size", 30)),
        max_pages=int(app_cfg.get("max_pages", 2)),
    )
    notifier = Notifier(token)
    targets = load_config_targets(cfg)
    return app_cfg, fetcher, notifier, targets


def main() -> None:
    parser = argparse.ArgumentParser(description="WishSale мониторинг объявлений")
    parser.add_argument("--once", action="store_true", help="один цикл сканирования и выход")
    parser.add_argument(
        "--force", action="store_true",
        help="повторить отправку всех подходящих объявлений (игнорировать дедупликацию)",
    )
    parser.add_argument(
        "--limit", type=int, default=0, metavar="N",
        help="отправить не более N объявлений (0 — без ограничения; удобно для теста)",
    )
    args = parser.parse_args()

    if (args.force or args.limit) and not args.once:
        sys.exit("--force и --limit используются только вместе с --once.")

    load_dotenv()
    token = os.environ.get("BOT_TOKEN")
    if not token:
        sys.exit("BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен.")
    raw_chats = os.environ.get("NOTIFY_CHAT_ID") or ""
    try:
        recipients = parse_recipients(raw_chats)
    except ValueError as exc:
        sys.exit(
            f"Некорректный NOTIFY_CHAT_ID ({raw_chats!r}): {exc}.\n"
            "Формат: chat_id или @username, опционально ':thread_id'."
        )
    if not recipients:
        sys.exit(
            "NOTIFY_CHAT_ID не задан. Укажите в .env chat_id (или @username канала),\n"
            "для топика форума — в формате chat_id:thread_id.\n"
            "Как узнать: напишите боту любое сообщение и запустите "
            "python scripts/get_chat_id.py"
        )

    root = Path(__file__).parent
    cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    app_cfg = cfg.get("app", {})
    setup_logging(app_cfg.get("log_dir", "logs"))

    store = Store(app_cfg.get("db_path", "data/wishsale.db"))
    _, fetcher, notifier, targets = build_runtime(cfg, token)

    log.info(
        "wishsale started: %d target(s), %d recipient(s)",
        len(targets), len(recipients),
    )

    if args.once:
        sent = scan_once(
            fetcher, store, notifier, targets, recipients,
            force=args.force, limit=args.limit,
        )
        log.info("done: %d notification(s) sent", sent)
        return

    interval = max(1, int(app_cfg.get("scan_interval_min", 10))) * 60
    jitter = int(app_cfg.get("jitter_sec", 120))
    log.info("scan every %ds (+0..%ds jitter)", interval, jitter)

    while True:
        # перечитываем config.yaml каждый цикл — правки без перезапуска
        current = load_config_targets(cfg)
        scan_once(fetcher, store, notifier, current, recipients)
        time.sleep(interval + random.uniform(0, jitter))


if __name__ == "__main__":
    main()
