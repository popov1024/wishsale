"""Отправка уведомлений в Telegram через Bot API (requests, синхронно)."""
from __future__ import annotations

import logging
from typing import Optional

import requests

from models import Ad

API = "https://api.telegram.org/bot{token}"
log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, token: str):
        self.base = API.format(token=token)
        self.session = requests.Session()

    def _post(self, method: str, payload: dict) -> bool:
        try:
            resp = self.session.post(
                f"{self.base}/{method}", json=payload, timeout=20
            )
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            log.error("telegram %s failed: %s", method, exc)
            return False
        if not data.get("ok"):
            log.error("telegram %s error: %s", method, data.get("description"))
            return False
        return True

    def send_ad(self, chat_id: int | str, target_name: str, ad: Ad, thread_id: int | None = None) -> bool:
        price = f"{ad.price_byn:g} BYN" if ad.price_byn is not None else "цена не указана"
        lines = [f"🔔 {target_name}", f"{ad.title} — {price}"]
        city = ad.city
        # Для Минска в ответе area — район города, помечаем город явно
        if str(ad.params.get("region", {}).get("v")) == "7":
            city = f"{city} (Минск)" if city else "Минск"
        if city:
            lines.append(f"📍 {city}")
        size = ad.param_label("sports_shoes_size")
        if size:
            lines.append(f"📏 Размер: {size}")
        lines.append(f"🛒 {ad.source} · 🔗 {ad.url}")
        caption = "\n".join(lines)

        if ad.images:
            payload = {"chat_id": chat_id, "photo": ad.images[0], "caption": caption}
            if thread_id is not None:
                payload["message_thread_id"] = thread_id
            return self._post("sendPhoto", payload)
        payload = {"chat_id": chat_id, "text": caption}
        if thread_id is not None:
            payload["message_thread_id"] = thread_id
        return self._post("sendMessage", payload)

    def send_text(self, chat_id: int | str, text: str, thread_id: int | None = None) -> bool:
        payload = {"chat_id": chat_id, "text": text}
        if thread_id is not None:
            payload["message_thread_id"] = thread_id
        return self._post("sendMessage", payload)
