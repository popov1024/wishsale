FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Minsk

WORKDIR /app

# Кэширование зависимостей: слой пересобирается только при изменении requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data /app/logs

# Контейнер работает от root: bind-mounted каталоги (./data, ./logs)
# на хосте могут принадлежать любому uid — root пишет в них без ошибок.
HEALTHCHECK --interval=1m --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/wishsale.db').execute('select 1')" || exit 1

CMD ["python", "main.py"]
