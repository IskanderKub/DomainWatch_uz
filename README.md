<p align="center"><img src="docs/logo.jpg" alt="DomainWatch.uz" width="640"></p>

# DomainWatch.uz

[English](#english) | [Русский](#русский)

## English

Availability monitoring for domains in the `.uz` zone with automatic detection of content tampering (defacement detection).

Every check saves a snapshot of the page text (MongoDB) and compares it with the previous snapshot using `difflib`. If text similarity drops below the threshold (`CONTENT_CHANGE_THRESHOLD`), the check is flagged as a suspected defacement.

### Stack

- **FastAPI** — REST API
- **SQLAlchemy 2.0 + PostgreSQL** — domains and check results
- **pymongo + MongoDB** — raw page text snapshots
- **requests + BeautifulSoup4** — HTTP checks and text extraction
- **difflib** — snapshot comparison
- **pandas** — statistics aggregation (uptime %, average response time)
- **APScheduler** — periodic automatic checks
- **pydantic-settings** — configuration from `.env`
- **pytest + pytest-mock + httpx** — tests

### Architecture

Layered architecture:

```
app/
├── api/            # HTTP layer: routers, FastAPI dependencies
│   └── v1/
├── services/        # business logic (domain checks, statistics)
├── repositories/     # data access (Postgres + MongoDB)
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
└── core/            # config, DB connections, scheduler
```

### Running with Docker

```bash
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`, the docs at `http://localhost:8000/docs`.

The dashboard (plain HTML/CSS/JS, no build step) opens at `http://localhost:8000/` — add domains, run checks, view statistics and check history. The UI is available in Russian and English (switch in the top-right corner). Its files live in [frontend/](frontend/) and are served by FastAPI itself via `StaticFiles`.

### Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # set your own POSTGRES_URL / MONGO_URL

uvicorn app.main:app --reload
```

### Tests

```bash
pytest
```

The tests use in-memory SQLite instead of PostgreSQL and mock HTTP requests and MongoDB, so no real services are required.

### Main endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/domains` | add a domain to monitoring |
| GET | `/api/v1/domains` | list domains |
| GET | `/api/v1/domains/{id}` | domain details |
| DELETE | `/api/v1/domains/{id}` | delete a domain |
| POST | `/api/v1/domains/{id}/checks` | run a check manually |
| GET | `/api/v1/domains/{id}/checks` | check history |
| GET | `/api/v1/domains/{id}/stats` | statistics (uptime %, average response time) |
| GET | `/api/v1/domains/{id}/checks/{check_id}/snapshot` | page text captured by a check |
| GET | `/api/v1/domains/{id}/defacements` | checks with global changes, plus the text diff |
| POST | `/api/v1/domains/{id}/archive-import` | re-import history from the Wayback Machine |

Active domains are checked automatically every `CHECK_INTERVAL_MINUTES` minutes (once an hour by default).

When a domain is added, its history for the last `ARCHIVE_BACKFILL_DAYS` days (one year by default) is imported from the Wayback Machine in the background. These checks are marked `source: "archive"`; they are excluded from uptime and average response time, but changes found in them are counted. To disable the import, set `ARCHIVE_IMPORT_ON_CREATE=false`.

The schema of an existing database is updated automatically on startup (see `app/core/migrations.py`).

---

## Русский

Мониторинг доступности доменов в зоне `.uz` с автоматическим обнаружением подмены контента (детекция дефейса).

При каждой проверке сохраняется снапшот текста страницы (MongoDB) и сравнивается с предыдущим снапшотом через `difflib`. Если схожесть текста падает ниже порога (`CONTENT_CHANGE_THRESHOLD`), проверка помечается как подозрение на дефейс.

### Стек

- **FastAPI** — REST API
- **SQLAlchemy 2.0 + PostgreSQL** — домены и результаты проверок
- **pymongo + MongoDB** — сырые снапшоты текста страниц
- **requests + BeautifulSoup4** — HTTP-проверки и извлечение текста
- **difflib** — сравнение снапшотов
- **pandas** — агрегация статистики (uptime%, среднее время ответа)
- **APScheduler** — периодические автопроверки
- **pydantic-settings** — конфигурация из `.env`
- **pytest + pytest-mock + httpx** — тесты

### Архитектура

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

### Запуск через Docker

```bash
cp .env.example .env
docker compose up --build
```

API будет доступно на `http://localhost:8000`, документация — на `http://localhost:8000/docs`.

Дашборд (простой HTML/CSS/JS, без сборки) открывается на `http://localhost:8000/` — добавление доменов, запуск проверок, статистика и история проверок. Интерфейс доступен на русском и английском (переключатель в правом верхнем углу). Файлы лежат в [frontend/](frontend/) и раздаются самим FastAPI через `StaticFiles`.

### Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # укажите свои POSTGRES_URL / MONGO_URL

uvicorn app.main:app --reload
```

### Тесты

```bash
pytest
```

Тесты используют SQLite in-memory вместо PostgreSQL и мокают HTTP-запросы и MongoDB — реальные сервисы не требуются.

### Основные эндпоинты

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
