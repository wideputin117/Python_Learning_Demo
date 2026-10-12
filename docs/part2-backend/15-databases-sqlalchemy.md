# 15 · Databases: SQLAlchemy 2.0 + Alembic

## Concept
**SQLAlchemy** is Python's standard database toolkit. It has two layers:
- **Core**: a SQL expression builder (`select(...)`, `insert(...)`) plus connection handling. Roughly what Knex is in Node.
- **ORM**: classes mapped to tables, with a **Session** that tracks changes and writes them in a
  transaction (unit of work). Roughly what TypeORM or MikroORM is in Node.

We use the **2.0 style**: typed models with `Mapped[...]`, queries built with `select()`, and the
**async** API (`AsyncSession`) so DB calls don't block FastAPI's event loop.

**Alembic** is SQLAlchemy's migration tool (`prisma migrate` / `knex migrate` equivalent). It can
**autogenerate** a migration by comparing your models with the actual database schema.

Key objects:
| Object | What it is |
|---|---|
| `Engine` (`create_async_engine`) | the connection pool, created **once per app** |
| `async_sessionmaker` | a factory that produces sessions |
| `AsyncSession` | one unit of work: tracks objects, runs queries, `commit()` / `rollback()`. **One per request.** |
| `DeclarativeBase` | the base class your models inherit from. It holds the `metadata` (all tables). |
| `Mapped[T]` + `mapped_column()` | typed column declarations |

We start with **SQLite** (a single file, zero setup) through the async driver **aiosqlite**. Switching
to Postgres later means changing `DATABASE_URL` to `postgresql+asyncpg://...` and installing `asyncpg`.
The models and queries stay the same.

## In Node you'd…
```prisma
// Prisma schema
model Ticket {
  id        String   @id @default(uuid())
  subject   String
  status    String   @default("open")
  createdAt DateTime @default(now())
  comments  Comment[]
}
```
```ts
const t = await prisma.ticket.create({ data: { subject: "Hi" } });
const open = await prisma.ticket.findMany({ where: { status: "open" }, orderBy: { createdAt: "desc" }, take: 20 });
await prisma.ticket.update({ where: { id }, data: { status: "closed" } });
```
```python
# SQLAlchemy 2.0
class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    comments: Mapped[list["Comment"]] = relationship(back_populates="ticket")

t = Ticket(subject="Hi")
session.add(t)
await session.commit()

result = await session.scalars(
    select(Ticket).where(Ticket.status == "open").order_by(Ticket.created_at.desc()).limit(20)
)
open_tickets = result.all()

t = await session.get(Ticket, ticket_id)
t.status = "closed"          # just mutate the object…
await session.commit()       # …the session notices and issues the UPDATE
```

| Prisma / TypeORM | SQLAlchemy 2.0 |
|---|---|
| `schema.prisma` / `@Entity()` | `class X(Base)` with `Mapped[...]` |
| `new PrismaClient()` / `DataSource` | `create_async_engine(url)` (once) |
| a transaction / `EntityManager` | `AsyncSession` (one per request) |
| `create({data})` | `session.add(obj)` + `commit()` |
| `findUnique({where:{id}})` | `await session.get(Model, id)` |
| `findMany({where, orderBy, take, skip})` | `select(M).where(...).order_by(...).limit().offset()` |
| `update` | mutate attributes + `commit()` |
| `delete` | `await session.delete(obj)` + `commit()` |
| `include: { comments: true }` | `.options(selectinload(Ticket.comments))` |
| `$transaction` | `async with session.begin(): ...` |
| `$queryRaw` | `await session.execute(text("SELECT ..."), {...})` |
| `prisma migrate dev` | `alembic revision --autogenerate -m "..."` + `alembic upgrade head` |
| `prisma migrate deploy` | `alembic upgrade head` |

## Examples

### 1. Install
```bash
uv add "sqlalchemy[asyncio]" aiosqlite alembic
```

### 2. Base class and engine/session setup
```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```
```python
# app/db/session.py
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

engine = create_async_engine(get_settings().database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    async with SessionLocal() as session:
        yield session
```
A function that `yield`s is a **generator dependency** (chapter 07). FastAPI runs the code
before `yield`, injects the value, runs your handler, then resumes after `yield` for cleanup.
`async with` closes the session, much like a `try/finally` around `client.release()` with `pg`.

`expire_on_commit=False` keeps object attributes readable after `commit()`. Without it, reading
`ticket.subject` after a commit would trigger a lazy reload, which **fails in async code**.

### 3. A typed model
```python
# app/models/ticket.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.schemas.ticket import TicketPriority, TicketStatus


def utcnow() -> datetime:
    return datetime.now(UTC)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    customer_email: Mapped[str] = mapped_column(String(320), index=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False, length=20), default=TicketStatus.OPEN, index=True
    )
    priority: Mapped[TicketPriority | None] = mapped_column(
        Enum(TicketPriority, native_enum=False, length=20)
    )
    category: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
```
- `Mapped[str]` gives `NOT NULL`. `Mapped[str | None]` gives a nullable column. The type hint drives nullability.
- `default=` is applied by SQLAlchemy in Python at INSERT time. `server_default=` is applied by the database.
- `onupdate=utcnow` sets `updated_at` on every UPDATE the ORM issues.
- `Enum(..., native_enum=False)` stores the enum *values* as `VARCHAR` with a CHECK constraint, which works the same on SQLite and Postgres.
- `uuid.UUID` maps to a native `UUID` on Postgres and `CHAR(32)` on SQLite, automatically.

### 4. Relationships (one-to-many)
```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Ticket(Base):
    # ...
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )

class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    ticket: Mapped["Ticket"] = relationship(back_populates="comments")
```
**In async code, never rely on lazy loading.** Accessing `ticket.comments` on an object loaded
without eager loading raises `MissingGreenlet`. Load relationships explicitly:
```python
from sqlalchemy.orm import selectinload

stmt = select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.comments))
ticket = (await session.scalars(stmt)).one_or_none()
```

### 5. CRUD
```python
from sqlalchemy import func, select

# CREATE
ticket = Ticket(subject="Refund", body="...", customer_email="a@b.c")
session.add(ticket)
await session.commit()
await session.refresh(ticket)            # reload server-generated values (if any)

# READ one by primary key
ticket = await session.get(Ticket, ticket_id)       # None if missing

# READ many with filters
stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(20).offset(0)
if status is not None:
    stmt = stmt.where(Ticket.status == status)       # build queries conditionally
tickets = list(await session.scalars(stmt))

# COUNT
total = await session.scalar(select(func.count()).select_from(Ticket))

# UPDATE: mutate + commit
for field, value in changes.items():
    setattr(ticket, field, value)
await session.commit()

# DELETE
await session.delete(ticket)
await session.commit()
```
`session.execute(stmt)` returns `Row` tuples. `session.scalars(stmt)` returns the first column of each
row, which for `select(Ticket)` means the `Ticket` objects. Use `scalars` for ORM queries.

Result helpers: `.all()`, `.first()`, `.one()` (exactly one or raise), `.one_or_none()`.

### 6. Transactions
```python
# Explicit block: commits on success, rolls back on exception
async with session.begin():
    session.add(ticket)
    session.add(Comment(ticket=ticket, text="auto-created"))
```
If an exception escapes a request before `commit()`, closing the session (when `get_session` exits)
rolls back the uncommitted work. Nothing half-written is saved.

### 7. Wiring it into FastAPI
```python
from typing import Annotated
from fastapi import Depends

SessionDep = Annotated[AsyncSession, Depends(get_session)]

@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: UUID, session: SessionDep) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket      # ORM object → TicketOut via from_attributes=True
```
`SessionDep` is a reusable alias. Chapter 16 explains dependency injection in depth.

### 8. Alembic: migrations
```bash
uv run alembic init -t async alembic        # creates alembic/ + alembic.ini, async template
```
Edit **`alembic/env.py`** so it knows your models and your URL:
```python
# alembic/env.py (the parts to change)
from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401  (import all models so Base.metadata knows every table)

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata
```
For SQLite, also enable **batch mode** (SQLite can't `ALTER` most columns) inside both
`context.configure(...)` calls: `render_as_batch=True`.

`app/models/__init__.py` should import every model (`from app.models.ticket import Ticket`), so that
`import app.models` registers them all.

Then:
```bash
uv run alembic revision --autogenerate -m "create tickets"   # writes alembic/versions/xxxx_create_tickets.py
# ALWAYS read the generated file before applying it
uv run alembic upgrade head          # apply
uv run alembic downgrade -1          # undo the last one
uv run alembic history               # list
uv run alembic current               # what the DB is at
```
A generated migration looks like this:
```python
def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        # ...
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"], unique=False)

def downgrade() -> None:
    op.drop_index(op.f("ix_tickets_status"), table_name="tickets")
    op.drop_table("tickets")
```

**Workflow** (same as Prisma): change the model, then `revision --autogenerate`, then review, then `upgrade head`, then commit the migration file.

### 9. Raw SQL when you need it
```python
from sqlalchemy import text

rows = await session.execute(
    text("SELECT category, COUNT(*) AS n FROM tickets GROUP BY category"),
)
for category, n in rows:
    print(category, n)
```
Always use bound parameters (`text("... WHERE id = :id"), {"id": x}`), never f-strings, because f-strings open you to SQL injection.

## Gotchas
- **`MissingGreenlet` errors** almost always mean lazy loading happened in async code. Fixes:
  `selectinload(...)`, `expire_on_commit=False`, or `await session.refresh(obj, ["relationship"])`.
- **Forgetting `await`.** `session.get(...)` without `await` returns a coroutine, not a ticket.
  Pyright/Pylance flags this. Read those warnings.
- **Forgetting `commit()`.** Changes are silently discarded when the session closes. Unlike
  Prisma, nothing is saved until you commit.
- **One session per request, never global.** Sessions aren't safe to share across concurrent requests. The *engine* is global, and *sessions* come from the dependency.
- **Autogenerate isn't magic.** It doesn't detect renames (it sees a drop plus an add, which **loses data**),
  and some type or constraint changes. Always read the migration.
- **Models must be imported** before autogenerate, or Alembic thinks the tables should be dropped.
- **Never `Base.metadata.create_all()` in production.** That's fine for tests, but use migrations for real DBs.
- **SQLite quirks:** no real `ALTER COLUMN` (use batch mode), loose typing, and stored datetimes lose
  their timezone (they come back naive). Treat them as UTC. Postgres doesn't have these problems.
- **`triagedesk.db` is git-ignored.** Delete it and `alembic upgrade head` to start fresh.

## Exercises
1. In a scratch script (`uv run python scratch.py`) with `sqlite+aiosqlite:///:memory:`, create a `Note`
   model, call `Base.metadata.create_all` via `async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)`,
   insert three notes and query them back ordered by title.
2. Write a query that returns the number of tickets per status as a `dict[str, int]`.
3. What's the difference between `session.execute(select(Ticket))` and `session.scalars(select(Ticket))`?
4. Add a `Comment` model with a relationship. Load a ticket with its comments without triggering
   lazy loading.
5. Add a nullable `assignee_email` column to `Ticket`, autogenerate a migration, read it, apply it,
   then downgrade and upgrade again.

<details><summary>Answers</summary>

1. ```python
   import asyncio
   from sqlalchemy import String, select
   from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
   from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

   class Base(DeclarativeBase): ...
   class Note(Base):
       __tablename__ = "notes"
       id: Mapped[int] = mapped_column(primary_key=True)
       title: Mapped[str] = mapped_column(String(100))

   async def main() -> None:
       engine = create_async_engine("sqlite+aiosqlite:///:memory:")
       async with engine.begin() as conn:
           await conn.run_sync(Base.metadata.create_all)
       Session = async_sessionmaker(engine, expire_on_commit=False)
       async with Session() as s:
           s.add_all([Note(title=t) for t in ["b", "c", "a"]])
           await s.commit()
           print([n.title for n in await s.scalars(select(Note).order_by(Note.title))])

   asyncio.run(main())
   ```
2. ```python
   rows = await session.execute(select(Ticket.status, func.count()).group_by(Ticket.status))
   counts = {str(status): n for status, n in rows}
   ```
3. `execute` returns `Row` objects (tuples), so you'd need `row[0]` or `row.Ticket`. `scalars` unwraps the first column and gives you `Ticket` instances directly.
4. `select(Ticket).where(Ticket.id == tid).options(selectinload(Ticket.comments))`
5. `assignee_email: Mapped[str | None] = mapped_column(String(320))`, then `alembic revision --autogenerate -m "add assignee"`. The file should contain `op.add_column(...)` (inside `batch_alter_table` on SQLite).
</details>

## Apply to TriageDesk: M2
**Goal:** Tickets persist in SQLite through SQLAlchemy, the schema is created by an Alembic migration,
and the in-memory dict from M1 is gone. The API contract (paths, schemas, status codes) **does not change**.
The M1 tests should pass with only fixture changes.

**Packages**
```bash
uv add "sqlalchemy[asyncio]" aiosqlite alembic
```

**Files**
| File | Purpose |
|---|---|
| `app/db/__init__.py` | empty |
| `app/db/base.py` | `class Base(DeclarativeBase)` |
| `app/db/session.py` | `engine`, `SessionLocal`, `get_session()` yield-dependency, `SessionDep` alias |
| `app/models/__init__.py` | `from app.models.ticket import Ticket` (imports all models) |
| `app/models/ticket.py` | the `Ticket` ORM model (fields as in M1) |
| `app/api/routes/tickets.py` (edit) | handlers become `async def` and use `SessionDep` |
| `alembic.ini`, `alembic/env.py`, `alembic/versions/*_create_tickets.py` | migrations |
| `tests/conftest.py` | a test DB fixture + `dependency_overrides` |

**Endpoint spec:** identical to M1 (see [chapter 13](13-fastapi-basics.md#apply-to-triagedesk-m1-part-1-routes)).

**Acceptance criteria**
- [ ] `uv run alembic upgrade head` on an empty folder creates `triagedesk.db` with a `tickets` table
- [ ] `uv run alembic downgrade base` drops it cleanly
- [ ] Tickets survive a server restart
- [ ] List endpoint filtering and pagination happen **in SQL** (`.where`, `.limit`, `.offset`), not in Python
- [ ] Indexes on `status` and `customer_email`
- [ ] `updated_at` changes on PATCH, and `created_at` doesn't
- [ ] Tests use a **separate** database (in-memory SQLite or a temp file), never `triagedesk.db`
- [ ] All M1 tests pass. Add one test proving that data written by one request is readable by the next.
- [ ] `ruff` + `pytest` green

**Hints**
- Pydantic `TicketOut` already has `from_attributes=True`, so you can `return ticket` (the ORM object) directly.
- PATCH: `for k, v in payload.model_dump(exclude_unset=True).items(): setattr(ticket, k, v)`.
- In tests, create tables with `Base.metadata.create_all` (fast) rather than running Alembic.
- In-memory SQLite gives every *connection* its own empty DB. Use a temp file (`tmp_path` fixture),
  or `poolclass=StaticPool` with `connect_args={"check_same_thread": False}`, so every connection shares one in-memory DB.
- `TestClient` + async engine works fine. TestClient runs the app's event loop for you.

<details><summary>Reference sketch (peek only after trying)</summary>

The trickiest piece is the test DB override:
```python
# tests/conftest.py (partial)
import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")

    async def init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init())
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with TestSession() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    asyncio.run(engine.dispose())
```
And the list query:
```python
stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
if status_ is not None:
    stmt = stmt.where(Ticket.status == status_)
return list(await session.scalars(stmt))
```
</details>
