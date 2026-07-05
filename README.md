# approval-service

Backend-сервис согласования контента перед публикацией. Принимает заявки на
согласование, хранит их в рамках workspace и фиксирует итоговое решение
(approve / reject / cancel).

Внешние сущности (публикации, сценарии, пользователи, workspace) передаются
только как идентификаторы - соседние сервисы здесь не реализуются.

Стек: **Python + FastAPI**, **SQLAlchemy 2.0 (async)**, **Alembic**,
PostgreSQL (docker-compose) или SQLite (локально).

---

## Быстрый старт через Docker

```bash
docker compose up --build
```

Поднимется PostgreSQL и сервис на `http://localhost:8000`. Миграции применяются
автоматически при старте контейнера (см. `entrypoint.sh`).

Проверка:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Swagger UI: `http://localhost:8000/docs`.

---

## Локальный запуск без Docker (SQLite)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# по умолчанию  SQLite (./approval.db)
export DATABASE_URL="sqlite+aiosqlite:///./approval.db"

alembic upgrade head
uvicorn app.main:app --reload
```

## Тесты

```bash
source .venv/bin/activate
pytest
```

Тесты используют изолированную временную SQLite-базу (fixture создаёт свежую БД
на каждый тест), внешние сервисы не нужны.

---

## Auth (заглушка для локального запуска)

Полноценной аутентификации нет - вместо неё каждый запрос несёт контекст в
HTTP-заголовках. Подпись/проверка токена не выполняется, это осознанная
заглушка для локальной разработки.

| Заголовок          | Назначение                                   | Пример                                              |
| ------------------ | -------------------------------------------- | --------------------------------------------------- |
| `X-Workspace-Id`   | workspace, от имени которого идёт запрос      | `ws_1`                                              |
| `X-User-Id`        | пользователь-инициатор                        | `usr_1`                                             |
| `X-Actions`        | список разрешённых действий через запятую      | `approval:read,approval:create,approval:decide,approval:cancel` |

Правила:

- `X-Workspace-Id` должен совпадать с `{workspace_id}` в URL, иначе `403`.
- Отсутствие `X-Workspace-Id` / `X-User-Id` → `401`.
- Для эндпоинта нужно соответствующее действие в `X-Actions`, иначе `403`.

| Действие          | Когда нужно      | Эндпоинты                    |
| ----------------- | ---------------- | ---------------------------- |
| `approval:read`   | чтение заявок    | `GET` list / one             |
| `approval:create` | создание заявки  | `POST` create                |
| `approval:decide` | approve / reject | `POST` approve, reject       |
| `approval:cancel` | cancel           | `POST` cancel                |

---

## API

```
GET    /health
GET    /ready

POST   /api/v1/workspaces/{workspace_id}/approval-requests
GET    /api/v1/workspaces/{workspace_id}/approval-requests
GET    /api/v1/workspaces/{workspace_id}/approval-requests/{request_id}

POST   /api/v1/workspaces/{workspace_id}/approval-requests/{request_id}/approve
POST   /api/v1/workspaces/{workspace_id}/approval-requests/{request_id}/reject
POST   /api/v1/workspaces/{workspace_id}/approval-requests/{request_id}/cancel
```

### Создание заявки

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/ws_1/approval-requests \
  -H "X-Workspace-Id: ws_1" \
  -H "X-User-Id: usr_1" \
  -H "X-Actions: approval:create" \
  -H "Idempotency-Key: 5f3c-once" \
  -H "Content-Type: application/json" \
  -d '{
        "sourceType": "publication",
        "sourceId": "pub_123",
        "title": "Instagram reel draft",
        "description": "Needs final approval",
        "reviewerUserIds": ["usr_1", "usr_2"]
      }'
```

`sourceType`: `publication` | `scenario` | `edit` | `external`.

Ответ `201`:

```json
{
  "id": "areq_4a18d766915c4c25b5c187b95f3782b8",
  "workspaceId": "ws_1",
  "sourceType": "publication",
  "sourceId": "pub_123",
  "title": "Instagram reel draft",
  "description": "Needs final approval",
  "reviewerUserIds": ["usr_1", "usr_2"],
  "status": "pending",
  "decision": null,
  "createdBy": "usr_1",
  "createdAt": "2026-07-03T12:30:34",
  "updatedAt": "2026-07-03T12:30:34"
}
```

### Решения

```bash
# approve
curl -X POST .../approval-requests/{id}/approve -d '{"comment": "Approved"}'   ...
# reject
curl -X POST .../approval-requests/{id}/reject  -d '{"reason": "Brand tone is wrong"}' ...
# cancel
curl -X POST .../approval-requests/{id}/cancel  -d '{"reason": "Draft was removed"}'   ...
```

Статусы: `pending → approved | rejected | cancelled`. Все три - финальные.
Повторное применение того же решения возвращает `200` (идемпотентно); попытка
перейти в другое финальное состояние - `409`.

### Идемпотентность

Для `POST`-запросов (create и решения) можно передать заголовок
`Idempotency-Key`. Повтор с тем же ключом и тем же телом вернёт сохранённый
ответ и не создаст дубль. Тот же ключ с другим телом → `409`.

### Список

```
GET /api/v1/workspaces/{workspace_id}/approval-requests?status=pending&limit=50&offset=0
```

### Формат ошибок

```json
{ "error": { "code": "invalid_transition", "message": "..." } }
```

---

## Струтура проекта

```
app/
  main.py            - сборка FastAPI-приложения
  config.py          - настройки (env / .env)
  db.py              - async engine и session
  models.py          - SQLAlchemy-модели
  schemas.py         - Pydantic-схемы (camelCase, strict input)
  auth.py            - auth-заглушка и проверка действий
  logging.py         - логирование + редакция секретов
  repository.py      - доступ к данным (scoped by workspace)
  service.py         - бизнес-логика: state machine, идемпотентность
  events.py          - аудит-лог и transactional outbox
  errors.py          - доменные ошибки и обработчики
  api/
    health.py
    approval_requests.py
migrations/          - Alembic
tests/               - pytest
```

Подробнее об архитектурных решениях - в [DESIGN.md](DESIGN.md).
