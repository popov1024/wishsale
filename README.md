# WishSale — мониторинг объявлений Kufar с уведомлениями в Telegram

Следит за объявлениями на Kufar по таргетам (запрос + города + фильтры)
и присылает найденное в указанный чат или канал Telegram.

Интерактивного бота с командами нет: уведомления просто уходят
в один (или несколько) фиксированных чатов через Bot API.

## Быстрый старт (локально)

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# 1) впишите BOT_TOKEN от @BotFather
# 2) впишите NOTIFY_CHAT_ID (куда слать уведомления)

# Узнать свой chat_id: напишите боту любое сообщение (например, /start), затем:
.venv/bin/python scripts/get_chat_id.py
#    → NOTIFY_CHAT_ID=123456789

# Проверка: один цикл сканирования (найденные объявления уйдут в Telegram)
.venv/bin/python main.py --once

# Постоянная работа
.venv/bin/python main.py
```

## Куда приходят уведомления (NOTIFY_CHAT_ID)

В `.env` задаётся получатель:

```env
NOTIFY_CHAT_ID=123456789        # личный чат или группа (число)
# NOTIFY_CHAT_ID=@my_channel    # или канал по @username
# NOTIFY_CHAT_ID=-100123:42     # топик форума/супергруппы (chat_id:thread_id)
# NOTIFY_CHAT_ID=123,456:7      # можно несколько через запятую
```

- **Личный чат** — напишите боту любое сообщение, и он сможет вам писать.
- **Группа** — добавьте бота в группу, укажите её id.
- **Канал** — добавьте бота администратором канала и укажите `@username`.
- **Топик форума/супергруппы** — формат `chat_id:thread_id`, бот должен быть
  участником группы (или администратором темы).

Узнать chat_id (и thread_id, если пишете в топик):
`python scripts/get_chat_id.py` — напишите боту сообщение в нужном топике
и запустите скрипт.

## Запуск через Docker

```bash
docker compose up -d --build
docker compose logs -f wishsale
docker compose down        # остановка (данные в ./data и ./logs сохраняются)
```

Тома:
- `./data` — SQLite-база (переживает пересоздание контейнера);
- `./logs` — логи приложения (`wishsale.log`);
- `./config.yaml` — монтируется read-only, правки без пересборки.

Контейнер работает от root, поэтому прав на запись в `./data` и `./logs`
хватает независимо от владельца этих каталогов на хосте.

## Telegram API и прокси

В Беларуси `api.telegram.org` заблокирован, поэтому нужен доступ:

1. **Вариант А — прокси**: укажите в `.env` `HTTPS_PROXY` (например, `socks5h://127.0.0.1:1080`
   если локально поднят VPN). `requests` подхватывает его автоматически.
2. **Вариант Б — VPS вне РБ**: соберите образ на сервере (`docker compose up -d --build`)
   — на VPS Telegram API доступен без прокси.

## Настройка таргетов (config.yaml)

```yaml
targets:
  - name: "Фигурные коньки Graf / Edea / Risport 37"
    query: "коньки"
    category: 4020                    # опционально
    regions:
      - { rgn: 2, ar: 5, label: "Гомель" }   # Гомельская обл. / Гомель
      - { rgn: 7, label: "Минск" }            # Минск — отдельный регион rgn=7
    must_contain: [graf, edea, risport]       # OR; для AND — all_keywords: true
    must_not_contain: [хоккейн, детск]        # антимусор
    params:                                   # фильтр по параметрам Kufar
      sports_shoes_size: { min: 37, max: 37 }
```

Справочник регионов Kufar: 1 Брестская, 2 Гомельская, 3 Гродненская, 4 Могилёвская,
5 Минская область, 6 Витебская, **7 = Минск**. Город внутри области — параметр `ar`
(Гомель = `ar: 5`).

`config.yaml` перечитывается при каждом скане — правки работают без перезапуска.

## Команды

| Команда | Действие |
|---|---|
| `python main.py` | постоянная работа: сканы по расписанию + рассылка |
| `python main.py --once` | один цикл сканирования |
| `python main.py --once --force --limit 3` | тест: повторно отправить до 3 объявлений (игнорируя дедупликацию) |
| `python scripts/get_chat_id.py` | узнать ваш chat_id для NOTIFY_CHAT_ID |
| `pytest` | запуск тестов |

## Структура

```
config.yaml          # настройки + таргеты
models.py            # Ad, Target
fetchers/kufar.py    # REST-клиент Kufar
rules.py             # правило-движок (цена/слова/параметры/город)
store.py             # SQLite: дедупликация объявлений
notifier.py          # отправка в Telegram
main.py              # планировщик сканов
scripts/get_chat_id.py
Dockerfile, docker-compose.yml
```
