"""Узнать chat_id (и thread_id) вашего чата для NOTIFY_CHAT_ID.

Как пользоваться:
1. Убедитесь, что BOT_TOKEN в .env — от того бота, которому вы пишете
   (скрипт сам покажет @username бота).
2. Напишите боту сообщение:
   - личный чат: любое сообщение (/start);
   - группа: добавьте бота в участники и отправьте команду /start
     или ответьте на сообщение бота (у бота включён privacy mode);
   - канал: бот должен быть администратором канала.
3. Запустите: python scripts/get_chat_id.py
4. Скрипт выведет NOTIFY_CHAT_ID=<chat_id>[:thread_id] — вставьте в .env.

Примечание: getUpdates возвращает только новые непрочитанные сообщения
за последние 24 часа, поэтому пишите боту и сразу запускайте скрипт.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
token = os.environ.get("BOT_TOKEN")
if not token:
    sys.exit("BOT_TOKEN не задан в .env.")

API = f"https://api.telegram.org/bot{token}"

# Показываем, какому боту принадлежит токен (частый источник ошибок — не тот бот)
me = requests.get(f"{API}/getMe", timeout=15).json()
if not me.get("ok"):
    sys.exit(f"getMe failed: {me.get('description')} — проверьте BOT_TOKEN в .env")
bot = me.get("result", {})
print(f"Бот: @{bot.get('username')} ({bot.get('first_name', '')})")

resp = requests.get(f"{API}/getUpdates", timeout=15).json()
if not resp.get("ok"):
    sys.exit(f"getUpdates failed: {resp.get('description')}")

updates = resp.get("result", [])
if not updates:
    sys.exit(
        "\nОбновлений нет — сообщения до бота не дошли. Проверьте:\n"
        f"1. Вы пишете именно боту @{bot.get('username')}, а не другому.\n"
        "2. Сообщение отправлено ПОСЛЕДНИМ и после него скрипт ещё не запускался\n"
        "   (getUpdates видит только новые сообщения за 24 ч).\n"
        "3. ЛИЧНЫЙ чат: откройте диалог с ботом (кнопка Start) и напишите /start.\n"
        "4. ГРУППА: бот добавлен в участники; из-за privacy mode он видит только\n"
        "   команды (/start) или ответы на его сообщения — обычный текст не видит.\n"
        "5. КАНАЛ: бот назначен администратором канала.\n"
        "6. Если бот где-то запущен с webhook — getUpdates не работает\n"
        "   (сейчас webhook не установлен, поэтому пункт неактуален).\n"
    )

for upd in reversed(updates):
    msg = (
        upd.get("message")
        or upd.get("edited_message")
        or upd.get("channel_post")
        or upd.get("edited_channel_post")
        or {}
    )
    chat = msg.get("chat", {})
    if chat.get("id"):
        chat_id = chat["id"]
        thread_id = msg.get("message_thread_id")
        print(
            f"\nNOTIFY_CHAT_ID={chat_id}"
            + (f":{thread_id}" if thread_id is not None else "")
        )
        if thread_id is not None:
            print(f"  (топик/тред: thread id={thread_id})")
        if chat.get("type") == "channel":
            print(f"канал @{chat.get('username')} — можно указать и так")
        sys.exit(0)

# Обновления есть, но без понятного chat_id — покажем, что нашлось
print("\nНайденные обновления:")
for upd in updates:
    for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
        m = upd.get(key)
        if m and m.get("chat", {}).get("id"):
            print(f"  {key}: chat_id={m['chat']['id']}")
sys.exit("Не удалось определить chat_id.")
