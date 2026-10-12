# 13 · FastAPI basics

## Concept
**FastAPI** is a web framework built on two libraries:
- **Starlette** handles HTTP: routing, requests/responses, middleware, WebSockets.
- **Pydantic** handles data: parsing, validation and serialization (chapter 14).

What makes FastAPI different is that **your function signature *is* the API contract**. FastAPI
reads the type hints on your handler and from them:
1. pulls each parameter from the right place (path, query string, JSON body, headers…),
2. validates and converts it (`"42"` → `42`, or a 422 error if it can't),
3. serializes your return value to JSON,
4. generates an **OpenAPI schema** and interactive docs at `/docs` (Swagger UI) and `/redoc`.

You write less glue code than in Express, and the docs can't drift from the code because they
*are* the code.

An app has three building blocks:
- `FastAPI()`: the application (like `express()`).
- `APIRouter()`: a group of routes you mount on the app (like `express.Router()`).
- **Path operations**: functions decorated with `@router.get(...)`, `@router.post(...)` and so on (decorators are covered in chapter 08).

FastAPI runs on an **ASGI server**, usually **uvicorn** (ASGI is to Python roughly what Node's
`http` server is to Express). `fastapi dev` starts uvicorn with auto-reload and `fastapi run` starts
it in production mode.

## In Node you'd…
```js
// Express
const express = require("express");
const { z } = require("zod");
const app = express();
app.use(express.json());

const CreateTicket = z.object({ subject: z.string().min(3), body: z.string() });

app.get("/tickets/:id", (req, res) => {
  const id = Number(req.params.id);          // manual conversion
  if (Number.isNaN(id)) return res.status(400).json({ error: "bad id" });
  res.json({ id });
});

app.post("/tickets", (req, res) => {
  const parsed = CreateTicket.safeParse(req.body);   // manual validation
  if (!parsed.success) return res.status(400).json(parsed.error);
  res.status(201).json({ id: 1, ...parsed.data });
});

app.listen(3000);
```
```python
# FastAPI: conversion, validation, error responses and docs are automatic
from fastapi import FastAPI, status
from pydantic import BaseModel, Field

app = FastAPI()

class CreateTicket(BaseModel):
    subject: str = Field(min_length=3)
    body: str

@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int) -> dict[str, int]:   # "abc" → automatic 422
    return {"id": ticket_id}

@app.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(payload: CreateTicket) -> dict:
    return {"id": 1, **payload.model_dump()}
```

| Express / Fastify | FastAPI |
|---|---|
| `express()` | `FastAPI()` |
| `express.Router()` + `app.use("/x", router)` | `APIRouter(prefix="/x")` + `app.include_router(router)` |
| `req.params.id` | parameter named like `{id}` in the path |
| `req.query.limit` | any simple-typed parameter not in the path |
| `req.body` (+ `express.json()`) | a parameter typed as a Pydantic model |
| `req.headers["x-api-key"]` | `x_api_key: Annotated[str, Header()]` |
| `res.status(201).json(x)` | `status_code=201` on the decorator, `return x` |
| `res.status(404).json(...)` early return | `raise HTTPException(status_code=404, detail="...")` |
| Fastify JSON schema / `@fastify/swagger` | built in: `/docs`, `/redoc`, `/openapi.json` |
| `nodemon app.js` | `fastapi dev app/main.py` |
| `node app.js` (prod) | `fastapi run app/main.py` (or `uvicorn app.main:app`) |
| supertest | `fastapi.testclient.TestClient` |

The biggest mental shift is that **you rarely touch the request object**. You declare what you need
and FastAPI hands it to you already validated.

## Examples

### 1. Path parameters
```python
from uuid import UUID
from fastapi import APIRouter

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("/{ticket_id}")
def get_ticket(ticket_id: UUID) -> dict[str, str]:
    # "/tickets/not-a-uuid" → 422 with a clear error, and your code never runs
    return {"id": str(ticket_id)}
```
The name in `{ticket_id}` must match the parameter name.

### 2. Query parameters, with defaults and constraints
```python
from typing import Annotated, Literal
from fastapi import Query

@router.get("")
def list_tickets(
    status: Literal["open", "in_progress", "resolved", "closed"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    q: Annotated[str | None, Query(max_length=100, description="Search in subject")] = None,
) -> dict:
    return {"status": status, "limit": limit, "offset": offset, "q": q}
```
`GET /tickets?status=open&limit=5` gives `status="open", limit=5`. `GET /tickets?limit=500` gives a 422.
Any parameter with a simple type (`int`, `str`, `bool`, `Literal`, `Enum`, `UUID`…) that isn't in the path is a query parameter.

`Annotated[int, Query(ge=1)]` means "the type is `int`, and here's extra metadata for FastAPI".
This `Annotated` style is the modern recommendation. You'll also see the older `limit: int = Query(20, ge=1)` in tutorials.

### 3. Request body with a Pydantic model
```python
from pydantic import BaseModel, EmailStr, Field

class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=1)
    customer_email: EmailStr

@router.post("", status_code=201)
def create_ticket(payload: TicketCreate) -> TicketCreate:
    return payload
```
Sending `{"subject": "Hi"}` gets a **422 Unprocessable Entity** listing every problem at once:
```json
{"detail": [
  {"type": "string_too_short", "loc": ["body", "subject"], "msg": "String should have at least 3 characters", ...},
  {"type": "missing", "loc": ["body", "body"], "msg": "Field required", ...},
  {"type": "missing", "loc": ["body", "customer_email"], "msg": "Field required", ...}
]}
```
FastAPI picks the source by type: **Pydantic model → body; simple type → query; name in path → path.**

### 4. Response models: control what goes out
```python
from datetime import datetime
from uuid import UUID, uuid4

class TicketOut(BaseModel):
    id: UUID
    subject: str
    created_at: datetime

@router.post("", status_code=201, response_model=TicketOut)
def create_ticket(payload: TicketCreate) -> dict:
    # Extra keys (like "internal_notes") are filtered out by response_model.
    return {"id": uuid4(), "subject": payload.subject, "created_at": datetime.now(),
            "internal_notes": "secret"}
```
The return type annotation (`-> TicketOut`) does the same job as `response_model=TicketOut`. Use the
return annotation when you return exactly that model, and `response_model=` when you return something else
(a dict, an ORM object) that should be *shaped* into the model. Response models are your defense against
leaking fields such as `password_hash`.

### 5. Errors with HTTPException
```python
from fastapi import HTTPException, status

FAKE_DB: dict[UUID, dict] = {}

@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: UUID) -> dict:
    ticket = FAKE_DB.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket
```
`raise` replaces Express's `return res.status(404).json(...)`. The exception bubbles out of any depth
of function calls and FastAPI turns it into `{"detail": "Ticket not found"}` with status 404.
(Chapter 16 adds domain exceptions so services don't need to know about HTTP.)

### 6. Status codes and empty responses
```python
from fastapi import Response

@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: UUID) -> Response:
    FAKE_DB.pop(ticket_id, None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```
Use the `status.HTTP_*` constants rather than magic numbers. They autocomplete and read better.

### 7. Headers, cookies, and the raw request (escape hatch)
```python
from fastapi import Header, Request

@router.get("/debug")
def debug(request: Request, user_agent: Annotated[str | None, Header()] = None) -> dict:
    # Header names: user_agent ↔ "User-Agent" (underscores become dashes automatically)
    return {"ua": user_agent, "client": request.client.host if request.client else None,
            "path": request.url.path}
```

### 8. Routers and the app factory (how TriageDesk is organized)
```python
# app/api/routes/tickets.py
router = APIRouter(prefix="/tickets", tags=["tickets"])

# app/main.py
from app.api.routes import health, tickets

def create_app() -> FastAPI:
    app = FastAPI(title="TriageDesk")
    app.include_router(health.router)
    app.include_router(tickets.router)
    return app

app = create_app()
```
`tags` group endpoints in `/docs`. The **factory** (`create_app()`) gives each test a fresh app, which
matters once you add overrides and state.

### 9. `def` vs `async def` handlers
```python
@router.get("/sync")
def sync_handler() -> dict:          # runs in a thread pool, so blocking code is OK here
    return {"ok": True}

@router.get("/async")
async def async_handler() -> dict:   # runs on the event loop, so NEVER block in here
    return {"ok": True}
```
Rule of thumb (more in chapter 11): if the handler `await`s something (an async DB, httpx, the Anthropic
async client), use `async def`. If it calls blocking libraries, use plain `def`. **Never call blocking I/O
(`time.sleep`, `requests.get`) inside `async def`.** It freezes every request, exactly like a blocking `fs.readFileSync` loop in Node.

### 10. Testing with TestClient
```python
from fastapi.testclient import TestClient
from app.main import create_app

def test_create_ticket_validates() -> None:
    client = TestClient(create_app())
    resp = client.post("/tickets", json={"subject": "x"})
    assert resp.status_code == 422
```
`TestClient` calls your app in-process. No server or port is needed, like supertest's `request(app)`.

### 11. Running it
```bash
uv run fastapi dev app/main.py           # http://127.0.0.1:8000, auto-reload
uv run fastapi dev app/main.py --port 8001
uv run fastapi run app/main.py           # production mode: no reload, listens on 0.0.0.0
```
Open **http://localhost:8000/docs**. Every endpoint is listed with its schema and a "Try it out"
button. It is effectively a free Postman collection.

## Gotchas
- **Route order matters.** `GET /tickets/{ticket_id}` declared before `GET /tickets/stats` will try to
  parse `"stats"` as a UUID and give a 422. Declare static paths first, the same as in Express.
- **422, not 400.** FastAPI's validation failures are `422 Unprocessable Entity`. Your Node frontend
  may expect 400. You can override this with a custom handler (chapter 16), but most teams keep 422.
- **A `dict` parameter is a body, not a query.** `def f(filters: dict)` expects JSON. For lists in
  query strings, use `tags: Annotated[list[str] | None, Query()] = None` → `?tags=a&tags=b`.
- **Trailing slashes.** `/tickets/` and `/tickets` differ, and FastAPI redirects (307) to the declared one.
  With `prefix="/tickets"`, declare the collection route as `""` (gives `/tickets`) rather than `"/"`.
- **`response_model` filters but doesn't fix types.** If you return something that can't be coerced
  into the model, you get a 500 (`ResponseValidationError`), not a 422. That's a bug in *your* code.
- **Mutable module-level dicts as a "DB"** are fine for M1, but they're shared across requests and
  reset on every reload. That's why M2 moves to a real database.
- **`fastapi dev` only reloads on file changes under the project.** Changes to `.env` need a manual restart.

## Exercises
1. Add `GET /echo/{word}` that returns `{"word": word, "length": len(word)}`, plus an optional query
   parameter `upper: bool = False`. Try `?upper=true`, `?upper=1` and `?upper=yes`. What does FastAPI accept?
2. Write a `POST /sum` that takes a body `{"numbers": [1, 2, 3]}` and returns their sum. Then send
   `{"numbers": ["1", "x"]}`. What's in the 422 response's `loc`?
3. Write `GET /items/{item_id}` (int) and `GET /items/latest`, in that order. Call `/items/latest`.
   What happens, and how do you fix it?
4. Make a response model `UserOut(id: int, email: str)` and an endpoint that returns
   `{"id": 1, "email": "a@b.c", "password": "hunter2"}`. Confirm the password is not in the response.
5. Write a TestClient test for exercise 2 that asserts both the happy path and the 422.

<details><summary>Answers</summary>

1. `true/false`, `1/0`, `yes/no` and `on/off` (case-insensitive) are all accepted as booleans. Anything else is a 422.
2. `loc` is `["body", "numbers", 1]`. It points at index 1 (`"x"`). `"1"` is coerced to `1` in the default (lax) mode.
3. `/items/latest` matches `/items/{item_id}` first and `"latest"` isn't an int, so you get a 422. Fix: declare `/items/latest` *before* `/items/{item_id}`.
4. ```python
   class UserOut(BaseModel):
       id: int
       email: str

   @app.get("/me", response_model=UserOut)
   def me() -> dict:
       return {"id": 1, "email": "a@b.c", "password": "hunter2"}
   ```
5. ```python
   def test_sum() -> None:
       client = TestClient(app)
       assert client.post("/sum", json={"numbers": [1, 2, 3]}).json() == {"total": 6}
       assert client.post("/sum", json={"numbers": ["x"]}).status_code == 422
   ```
</details>

## Apply to TriageDesk: M1 (part 1: routes)
M1 spans this chapter and [chapter 14](14-pydantic.md). This chapter covers the **routes**. Chapter 14
covers the **schemas**. Read both, then build M1.

**Goal:** Tickets CRUD with an in-memory store. No database yet (that's M2).

**Packages:** none. `fastapi[standard]` already includes `email-validator` (for `EmailStr`).

**Files to create**
| File | Purpose |
|---|---|
| `app/schemas/__init__.py` | empty |
| `app/schemas/ticket.py` | `TicketStatus`, `TicketPriority`, `TicketCreate`, `TicketUpdate`, `TicketOut` (ch 14) |
| `app/api/routes/tickets.py` | `router = APIRouter(prefix="/tickets", tags=["tickets"])` + the 5 endpoints |
| `app/main.py` (edit) | `app.include_router(tickets.router)` |
| `tests/test_tickets.py` | endpoint tests |

**Endpoint spec** (no auth until M4: anyone can call everything)
| Method | Path | Request | Response | Status codes |
|---|---|---|---|---|
| POST | `/tickets` | `TicketCreate` body | `TicketOut` | 201, 422 |
| GET | `/tickets` | query: `status?`, `priority?`, `category?`, `limit` (1–100, default 20), `offset` (≥0, default 0) | `list[TicketOut]`, newest first | 200, 422 |
| GET | `/tickets/{ticket_id}` | `ticket_id: UUID` | `TicketOut` | 200, 404, 422 |
| PATCH | `/tickets/{ticket_id}` | `TicketUpdate` body (all fields optional) | `TicketOut` | 200, 404, 422 |
| DELETE | `/tickets/{ticket_id}` | — | empty | 204, 404 |

**Ticket fields:** `id` (UUID, server-generated), `subject`, `body`, `customer_email`, `status`
(`open|in_progress|resolved|closed`, default `open`), `priority` (`low|medium|high|urgent`, `null`
until triage), `category` (str, `null` until triage), `created_at`, `updated_at` (server-set, UTC).

**Acceptance criteria**
- [ ] `/docs` shows a **tickets** section with all five endpoints and their schemas
- [ ] POST returns 201 with a generated `id`, `status == "open"`, `priority == null`
- [ ] Client-sent `id`, `created_at` or `status` in POST are ignored (not part of `TicketCreate`)
- [ ] GET list filters by `status`/`priority`/`category` and paginates with `limit`/`offset`
- [ ] PATCH only changes the fields that were sent, and bumps `updated_at`
- [ ] Unknown id → 404 `{"detail": "Ticket not found"}` on GET/PATCH/DELETE
- [ ] Tests in `tests/test_tickets.py`: create (201), create invalid (422), get (200), get missing
      (404), list filter, PATCH partial update, delete then get (404)
- [ ] `uv run ruff check .` and `uv run pytest` pass

**Hints**
- Store tickets in a module-level `_TICKETS: dict[UUID, TicketOut] = {}` inside `tickets.py`. It's
  throwaway code: M2 replaces it with the DB and M3 moves the logic into a service.
- Use `datetime.now(UTC)` (`from datetime import UTC, datetime`), never naive `datetime.now()`.
- Tests share the module-level dict. Add a pytest fixture that calls `_TICKETS.clear()` (chapter 12).
- For PATCH, `payload.model_dump(exclude_unset=True)` gives only the fields the client actually sent (chapter 14).

<details><summary>Reference sketch (peek only after trying)</summary>

```python
# app/api/routes/tickets.py (partial)
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.ticket import TicketCreate, TicketOut, TicketPriority, TicketStatus, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])
_TICKETS: dict[UUID, TicketOut] = {}


def _get_or_404(ticket_id: UUID) -> TicketOut:
    ticket = _TICKETS.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.get("")
def list_tickets(
    status_: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: TicketPriority | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TicketOut]:
    tickets = sorted(_TICKETS.values(), key=lambda t: t.created_at, reverse=True)
    if status_ is not None:
        tickets = [t for t in tickets if t.status == status_]
    # ... priority / category filters ...
    return tickets[offset : offset + limit]


@router.patch("/{ticket_id}")
def update_ticket(ticket_id: UUID, payload: TicketUpdate) -> TicketOut:
    ticket = _get_or_404(ticket_id)
    changes = payload.model_dump(exclude_unset=True)
    updated = ticket.model_copy(update={**changes, "updated_at": datetime.now(UTC)})
    _TICKETS[ticket_id] = updated
    return updated
```
Why `status_` with `alias="status"`? Because `status` is already the imported `fastapi.status`
module. The alias keeps the public query name `?status=open`.
</details>
