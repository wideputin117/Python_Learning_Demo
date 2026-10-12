# 16 · Architecture: dependency injection, services, errors, middleware

## Concept
By M2 your route handlers do everything: parse input, query the DB, apply business rules, raise
HTTP errors. That's fine for five endpoints and painful for fifty. Once AI calls arrive in M6, which
need mocking in tests, it becomes untestable. This chapter introduces the structure TriageDesk
uses from M3 onward:

```
HTTP request
   │
   ▼
routes/      thin: parse + validate (Pydantic), call a service, shape the response
   │  Depends(...)
   ▼
services/    business logic: rules, orchestration, transactions. No FastAPI imports.
   │
   ▼
models/ + db/  persistence (SQLAlchemy)      ai/  LLM + vector store (M5+)
```

Four tools make this work:
1. **Dependency injection (`Depends`)**: FastAPI builds and injects whatever a handler needs (a session,
   a service, the current user, settings), and tests can **override** any of it.
2. **Domain exceptions**: services raise `NotFoundError` or `PermissionDeniedError`, not `HTTPException`.
   One **exception handler** maps them to HTTP responses.
3. **Middleware**: code that wraps every request (logging, request IDs, timing, CORS).
4. **Logging**: the standard `logging` module, configured once at startup.

## In Node you'd…
| Express / NestJS | FastAPI |
|---|---|
| middleware `(req, res, next)` that sets `req.user` | a **dependency** `get_current_user` that *returns* the user |
| NestJS `@Injectable()` providers + constructor injection | `Depends(factory)` in handler params |
| NestJS module overrides / jest.mock in tests | `app.dependency_overrides[dep] = fake` |
| `app.use((err, req, res, next) => ...)` error middleware | `@app.exception_handler(MyError)` |
| `class NotFoundError extends Error {}` | `class NotFoundError(AppError): ...` |
| `app.use(morgan("dev"))` | an `@app.middleware("http")` function, or a Starlette `BaseHTTPMiddleware` |
| `app.use(cors())` | `app.add_middleware(CORSMiddleware, ...)` |
| winston / pino | `logging` (stdlib), structlog for JSON logs later |
| `res.locals` | `request.state` |

The key difference from Express: **dependencies are per-parameter and typed**, not a global chain that
mutates `req`. A handler declares *exactly* what it needs. FastAPI resolves the graph (dependencies
can depend on other dependencies), caches each one per request, and runs any `yield` cleanup at the end.

## Examples

### 1. Dependencies: the basics
```python
from typing import Annotated
from fastapi import Depends, Query

def pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, int]:
    return {"limit": limit, "offset": offset}

Pagination = Annotated[dict[str, int], Depends(pagination)]

@router.get("/tickets")
async def list_tickets(page: Pagination) -> list[TicketOut]: ...

@router.get("/kb/documents")
async def list_docs(page: Pagination) -> list[KBDocumentOut]: ...
```
A dependency is any callable. Its own parameters are resolved the same way as a handler's (query, path,
headers, other dependencies). That's why `limit`/`offset` show up in `/docs` for both endpoints.

### 2. Dependency chains + caching
```python
async def get_session() -> AsyncIterator[AsyncSession]:       # from ch 15
    async with SessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

def get_ticket_service(session: SessionDep) -> TicketService:
    return TicketService(session)

TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]

@router.post("", status_code=201, response_model=TicketOut)
async def create_ticket(payload: TicketCreate, service: TicketServiceDep) -> Ticket:
    return await service.create(payload)
```
If two dependencies in the same request both need `SessionDep`, FastAPI calls `get_session`
**once** and shares the result. You get one session (one transaction) per request for free.

### 3. Class-based service (no FastAPI inside)
```python
# app/services/ticket_service.py
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate


class TicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: TicketCreate) -> Ticket:
        ticket = Ticket(**data.model_dump())
        self.session.add(ticket)
        await self.session.commit()
        return ticket

    async def get(self, ticket_id: UUID) -> Ticket:
        ticket = await self.session.get(Ticket, ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket", ticket_id)
        return ticket

    async def update(self, ticket_id: UUID, data: TicketUpdate) -> Ticket:
        ticket = await self.get(ticket_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(ticket, field, value)
        await self.session.commit()
        return ticket
```
This class could run from a CLI script, a background worker or a test, with no HTTP involved. In M6 it will
also receive a `TriageClient` (the AI wrapper) through its constructor, which tests replace with a fake.

### 4. Domain exceptions + one handler
```python
# app/core/errors.py
class AppError(Exception):
    """Base class for errors the API knows how to report."""
    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"

    def __init__(self, resource: str, resource_id: object) -> None:
        super().__init__(f"{resource} {resource_id} not found")


class PermissionDeniedError(AppError):
    status_code = 403
    code = "forbidden"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
```
```python
# app/core/errors.py (continued)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )
```
```python
# app/main.py
def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    register_exception_handlers(app)
    ...
```
The handler for `AppError` also catches every subclass. Keep the response shape `{"detail": ...}`
so it matches FastAPI's own `HTTPException` responses, and clients see one consistent format.

### 5. Middleware: request logging + request ID
```python
# app/core/middleware.py
import logging
import time
import uuid

from fastapi import FastAPI, Request

logger = logging.getLogger("triagedesk.request")

def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)            # ≈ Express next(), but you get the response back
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        logger.info("%s %s → %s (%.1f ms) [%s]", request.method, request.url.path,
                    response.status_code, elapsed_ms, request_id)
        return response
```
Unlike Express, where `next()` is fire-and-forget, `await call_next(request)` **returns the response**.
That makes "after" logic (timing, headers) a straight line of code instead of an `on("finish")` listener.

CORS (needed once a frontend calls the API):
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_methods=["*"], allow_headers=["*"])
```

### 6. Logging, configured once
```python
# app/core/logging.py
import logging

def setup_logging(debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
```
```python
# anywhere else
import logging
logger = logging.getLogger(__name__)      # e.g. "app.services.ticket_service"

logger.info("Created ticket %s", ticket.id)     # %-style args: formatted lazily, only if logged
logger.exception("Triage failed")               # inside except: logs the traceback too
```
`getLogger(__name__)` gives each module a named logger, so you can raise or lower verbosity per package
(`logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)` shows all SQL).

### 7. Overriding dependencies in tests
```python
class FakeTicketService:
    async def get(self, ticket_id):
        raise NotFoundError("Ticket", ticket_id)

def test_get_missing_returns_404() -> None:
    app = create_app()
    app.dependency_overrides[get_ticket_service] = lambda: FakeTicketService()
    client = TestClient(app)
    resp = client.get(f"/tickets/{uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
```
The key in `dependency_overrides` is the **original function object**. This is how M6 tests will
avoid calling Claude: override the AI client dependency with a fake.

### 8. Settings as a dependency
```python
SettingsDep = Annotated[Settings, Depends(get_settings)]

@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
```
In tests: `app.dependency_overrides[get_settings] = lambda: Settings(app_name="Test")`.

### 9. Dependencies on the router or the whole app
```python
router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])   # guards every route
```
Use `dependencies=[...]` when you need the side effect (an auth check) but not the value.

## Gotchas
- **Don't import FastAPI in services.** If `services/` imports `HTTPException`, the layering has
  leaked. Raise domain errors and let the handler translate them.
- **`Depends(get_session)`, not `Depends(get_session())`.** Pass the function and FastAPI calls it.
- **Override with the same callable you depend on.** Overriding `get_session` does nothing if
  your routes depend on a *different* function that happens to have the same name.
- **`yield` dependencies run cleanup after the response is sent.** Don't raise `HTTPException` after
  the `yield` (it's too late to change the response). Commit in the service, not in the dependency's cleanup.
- **Middleware sees every request, including `/docs`.** Keep it fast and never read the body in
  logging middleware, because that consumes the stream.
- **Exception handlers for `Exception`** catch everything, including bugs. Use them only for a
  generic 500 with logging. Don't leak tracebacks to clients.
- **`print()` isn't logging.** It has no levels, timestamps or routing. Use `logger`.
- **Don't over-abstract.** No repository-of-repositories, no interfaces for one implementation.
  `routes → services → models` is enough here. Add a layer when it removes pain.

## Exercises
1. Write a dependency `get_request_id(request: Request) -> str` that returns `request.state.request_id`
   (set by the middleware), and include it in an endpoint's response.
2. Create an `@app.exception_handler(RequestValidationError)` that returns status 400 and
   `{"detail": "Invalid input", "errors": exc.errors()}`. Then decide whether you want that (most APIs keep 422).
3. Make a dependency `require_header_token` that raises `HTTPException(401)` unless
   `X-Token: secret` is present, and attach it to a whole router with `dependencies=[...]`.
4. Write a test that overrides `get_settings` to return a custom `app_name` and checks `/health`.
5. Why is `TicketService.get()` raising `NotFoundError` better than returning `None` for the route to check?

<details><summary>Answers</summary>

1. ```python
   def get_request_id(request: Request) -> str:
       return getattr(request.state, "request_id", "unknown")
   ```
2. `from fastapi.exceptions import RequestValidationError`, then register the handler like the `AppError` one. Note that `exc.errors()` may include non-JSON-serializable context, so use `jsonable_encoder(exc.errors())`.
3. ```python
   def require_header_token(x_token: Annotated[str | None, Header()] = None) -> None:
       if x_token != "secret":
           raise HTTPException(status_code=401, detail="Missing or bad token")

   router = APIRouter(prefix="/private", dependencies=[Depends(require_header_token)])
   ```
4. Once `health` takes `SettingsDep` (Example 8): `app.dependency_overrides[get_settings] = lambda: Settings(app_name="X")`, then assert `client.get("/health").json()["app"] == "X"`.
5. Every caller gets the same behavior (404 with a consistent body). Nobody can forget the `None` check, and non-HTTP callers (scripts, workers) get a meaningful exception.
</details>

## Apply to TriageDesk: M3
**Goal:** Restructure the code without changing the API. Routes become thin, logic moves to
`TicketService`, errors are domain exceptions with one handler, every request is logged with an ID,
and tests get proper fixtures.

**Packages:** none new.

**Files**
| File | Purpose |
|---|---|
| `app/core/errors.py` | `AppError`, `NotFoundError`, `PermissionDeniedError`, `ConflictError`, `register_exception_handlers()` |
| `app/core/logging.py` | `setup_logging(debug)` |
| `app/core/middleware.py` | request-ID + timing log middleware, `register_middleware()` |
| `app/services/__init__.py` | empty |
| `app/services/ticket_service.py` | `TicketService` (create, get, list, update, delete) |
| `app/api/deps.py` | `SessionDep`, `SettingsDep`, `get_ticket_service`, `TicketServiceDep`, `Pagination` |
| `app/api/routes/tickets.py` (edit) | each handler is 1–3 lines calling the service |
| `app/main.py` (edit) | `setup_logging`, `register_exception_handlers`, `register_middleware` |
| `tests/conftest.py` (edit) | fixtures: `client`, `session`, `ticket_factory` |
| `tests/test_ticket_service.py` | service-level tests (no HTTP) |

**Behavior spec**
| Situation | Response |
|---|---|
| Unknown ticket id | 404 `{"detail": "Ticket <id> not found", "code": "not_found"}` |
| Validation error | 422 (FastAPI default, unchanged) |
| Unhandled exception | 500 `{"detail": "Internal server error"}`, with the traceback **logged**, not returned |
| Every response | has an `x-request-id` header (echoes the incoming one if present) |
| Every request | one INFO log line: method, path, status, duration, request id |

**Acceptance criteria**
- [ ] No route handler contains SQL or `session.` calls. Those live in `TicketService`.
- [ ] `app/services/` has zero `fastapi` imports (`grep -r "fastapi" app/services` is empty)
- [ ] Error responses are consistent: `{"detail", "code"}` for `AppError`s
- [ ] `x-request-id` is present on responses (test it)
- [ ] `tests/test_ticket_service.py` tests the service directly against the test DB, including
      `NotFoundError` being raised
- [ ] One test uses `app.dependency_overrides` with a fake service
- [ ] A `ticket_factory` fixture creates tickets for tests in one line
- [ ] All earlier tests still pass. `ruff` and `pytest` are green.

**Hints**
- Do it in small steps and run the tests after each: (1) move one endpoint to the service, (2) add
  errors + handler, (3) middleware, (4) logging, (5) refactor the tests.
- For the 500 handler, register `@app.exception_handler(Exception)` and use `logger.exception(...)`.
  `TestClient(app, raise_server_exceptions=False)` lets you test it.
- Async service tests need an event loop. Either run them with `asyncio.run(...)` inside a sync test, or
  `uv add --dev pytest-asyncio` and mark them `@pytest.mark.asyncio` (chapter 12).

<details><summary>Reference sketch (peek only after trying)</summary>

```python
# app/api/deps.py (partial)
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.ticket_service import TicketService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_ticket_service(session: SessionDep) -> TicketService:
    return TicketService(session)


TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]
```
```python
# app/api/routes/tickets.py (after M3, partial)
@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: UUID, service: TicketServiceDep) -> Ticket:
    return await service.get(ticket_id)
```
```python
# generic 500 handler
logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```
</details>
