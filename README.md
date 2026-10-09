# DomainWatch.uz

Мониторинг доступности доменов в зоне `.uz` с автоматическим обнаружением подмены контента (детекция дефейса).

При каждой проверке сохраняется снапшот текста страницы (MongoDB) и сравнивается с предыдущим снапшотом через `difflib`. Если схожесть текста падает ниже порога (`CONTENT_CHANGE_THRESHOLD`), проверка помечается как подозрение на дефейс.

## Стек

- **FastAPI** — REST API
- **SQLAlchemy 2.0 + PostgreSQL** — домены и результаты проверок
- **pymongo + MongoDB** — сырые снапшоты текста страниц
- **requests + BeautifulSoup4** — HTTP-проверки и извлечение текста
- **difflib** — сравнение снапшотов
- **pandas** — агрегация статистики (uptime%, среднее время ответа)
- **APScheduler** — периодические автопроверки
- **pydantic-settings** — конфигурация из `.env`
- **pytest + pytest-mock + httpx** — тесты

## Архитектура

Слоистая архитектура:

```
app/
├── api/            # HTTP-слой: роутеры, зависимости FastAPI
│   └── v1/
├── services/        # бизнес-логика (проверка доменов, статистика)
├── repositories/     # доступ к данным (Postgres + MongoDB)
├── models/          # SQLAlchemy ORM-модели
├── schemas/         # Pydantic-схемы запросов/ответов
└── core/            # конфиг, подключения к БД, планировщик
```

## Запуск через Docker

```bash
cp .env.example .env
docker compose up --build
```

API будет доступно на `http://localhost:8000`, документация — на `http://localhost:8000/docs`.

Дашборд (простой HTML/CSS/JS, без сборки) открывается на `http://localhost:8000/` — добавление доменов, запуск проверок, статистика и история проверок. Файлы лежат в [frontend/](frontend/) и раздаются самим FastAPI через `StaticFiles`.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # укажите свои POSTGRES_URL / MONGO_URL

uvicorn app.main:app --reload
```

## Тесты

```bash
pytest
```

Тесты используют SQLite in-memory вместо PostgreSQL и мокают HTTP-запросы и MongoDB — реальные сервисы не требуются.

## Основные эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/v1/domains` | добавить домен на мониторинг |
| GET | `/api/v1/domains` | список доменов |
| GET | `/api/v1/domains/{id}` | информация о домене |
| DELETE | `/api/v1/domains/{id}` | удалить домен |
| POST | `/api/v1/domains/{id}/checks` | выполнить проверку вручную |
| GET | `/api/v1/domains/{id}/checks` | история проверок |
| GET | `/api/v1/domains/{id}/stats` | статистика (uptime%, среднее время ответа) |
| GET | `/api/v1/domains/{id}/checks/{check_id}/snapshot` | текст страницы, полученный проверкой |
| GET | `/api/v1/domains/{id}/defacements` | проверки с глобальными изменениями и дифф текста |
| POST | `/api/v1/domains/{id}/archive-import` | заново импортировать историю из Wayback Machine |

Активные домены проверяются автоматически каждые `CHECK_INTERVAL_MINUTES` минут (по умолчанию — раз в час).

При добавлении домена в фоне импортируется его история из Wayback Machine за `ARCHIVE_BACKFILL_DAYS` дней (по умолчанию — год). Такие проверки помечены `source: "archive"`; в uptime и среднее время ответа они не входят, а найденные в них изменения учитываются. Отключить импорт: `ARCHIVE_IMPORT_ON_CREATE=false`.

Схема существующей базы обновляется автоматически при старте (см. `app/core/migrations.py`).
