# 14 · Pydantic deep dive & settings

## Concept
**Pydantic** turns type hints into runtime validation. You declare a class that inherits from
`BaseModel`, and Pydantic:
- **parses** input (dicts, JSON, ORM objects) into a typed instance,
- **validates** it (types, constraints, custom rules) and reports *every* error at once,
- **coerces** compatible values (`"42"` → `42`) in its default *lax* mode, or refuses them in *strict* mode,
- **serializes** back out with `model_dump()` (a dict) or `model_dump_json()` (a JSON string),
- produces a **JSON Schema**, which is how FastAPI builds `/docs`.

FastAPI uses Pydantic for request bodies, response models and (via `pydantic-settings`) app configuration.
Pydantic v2 has a Rust core, so it's fast. This chapter uses **v2 APIs only**. Many blog posts still
show v1 (`.dict()`, `class Config:`, `@validator`), and those are deprecated.

A typical API has several models per resource:
- `TicketCreate`: what the client may send on create
- `TicketUpdate`: what the client may send on update (everything optional)
- `TicketOut`: what the server returns (includes `id`, timestamps)

This split is the same idea as separate Zod schemas or DTO classes in NestJS. It's how you stop a
client from setting `id` or `status` on create, and stop `password_hash` from leaking out.

## In Node you'd…
```ts
// Zod
import { z } from "zod";

const TicketCreate = z.object({
  subject: z.string().min(3).max(200),
  body: z.string().min(1),
  customerEmail: z.string().email(),
  tags: z.array(z.string()).default([]),
});
type TicketCreate = z.infer<typeof TicketCreate>;
const t = TicketCreate.parse(req.body);           // throws ZodError
```
```python
# Pydantic: the class *is* both the schema and the type
from pydantic import BaseModel, EmailStr, Field

class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=1)
    customer_email: EmailStr
    tags: list[str] = []

t = TicketCreate.model_validate(data)              # raises ValidationError
```

| Zod / class-validator | Pydantic v2 |
|---|---|
| `z.object({...})` | `class X(BaseModel): ...` |
| `z.infer<typeof X>` | not needed: `X` is already the type |
| `X.parse(obj)` | `X.model_validate(obj)` or `X(**obj)` |
| `X.parse(JSON.parse(s))` | `X.model_validate_json(s)` (faster, single step) |
| `X.safeParse` | `try: ... except ValidationError as e: e.errors()` |
| `.optional()` | `field: str \| None = None` |
| `.default(v)` | `field: int = 0` / `Field(default_factory=list)` |
| `.min(3)` | `Field(min_length=3)` (str/list) or `Field(ge=3)` (numbers) |
| `z.enum([...])` | `Literal["a", "b"]` or a `StrEnum` |
| `.refine(fn)` | `@field_validator` / `@model_validator` |
| `.transform(fn)` | `@field_validator(mode="before"/"after")` returning the new value |
| `X.partial()` | a separate `XUpdate` model with all fields optional |
| `X.extend({...})` | subclassing: `class B(A): extra: int` |
| `.strict()` (unknown keys) | `model_config = ConfigDict(extra="forbid")` |
| `JSON.stringify(obj)` | `obj.model_dump_json()` |
| dotenv + `z.object(process.env)` | `pydantic_settings.BaseSettings` |

## Examples

### 1. Basics: parse, coerce, error
```python
from pydantic import BaseModel, ValidationError

class Point(BaseModel):
    x: int
    y: int = 0

Point(x="3")                 # Point(x=3, y=0)  (lax mode coerces "3" → 3)
Point.model_validate({"x": 1, "y": 2})

try:
    Point(x="abc")
except ValidationError as e:
    print(e.error_count())   # 1
    print(e.errors()[0]["loc"], e.errors()[0]["msg"])
    # ('x',) Input should be a valid integer, unable to parse string as an integer
```

### 2. Constraints with `Field` and `Annotated`
```python
from typing import Annotated
from pydantic import BaseModel, Field

Subject = Annotated[str, Field(min_length=3, max_length=200)]   # reusable constrained type

class TicketCreate(BaseModel):
    subject: Subject
    body: str = Field(min_length=1, description="Full ticket text from the customer")
    attachments: list[str] = Field(default_factory=list, max_length=5)
    score: float = Field(default=0.0, ge=0, le=1)
```
`description`, `examples` and `title` end up in `/docs`.

### 3. Enums for fixed choices
```python
from enum import StrEnum

class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Ticket(BaseModel):
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority | None = None

Ticket(status="resolved").status           # <TicketStatus.RESOLVED: 'resolved'>
Ticket(status="resolved").status == "resolved"   # True: StrEnum compares equal to its str
Ticket(status="banana")                    # ValidationError listing the allowed values
```
`StrEnum` (Python 3.11+) is better than `Literal[...]` when you'll reuse the values in code, the DB (M2)
and AI prompts (M6). It gives you one source of truth.

### 4. Nested models and lists
```python
class Citation(BaseModel):
    chunk_id: str
    source: str
    score: float

class DraftReply(BaseModel):
    text: str
    citations: list[Citation] = []

DraftReply.model_validate({"text": "Hi", "citations": [{"chunk_id": "c1", "source": "faq.md", "score": 0.82}]})
```
Errors in nested data report the full path, for example `("citations", 0, "score")`.

### 5. Field validators (`@field_validator`)
```python
from pydantic import BaseModel, field_validator

class TicketCreate(BaseModel):
    subject: str
    customer_email: str

    @field_validator("subject")
    @classmethod
    def strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("subject must not be blank")
        return v                       # the returned value is what gets stored

    @field_validator("customer_email", mode="before")
    @classmethod
    def lowercase_email(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v
```
- `mode="after"` (default) runs **after** type validation, so `v` is already a `str`.
- `mode="before"` runs on the raw input, so it could be anything. Check its type.
- Raise `ValueError` for invalid data. Pydantic wraps it in a `ValidationError`, and FastAPI turns that into a 422.

### 6. Model validators: rules across fields
```python
from typing import Self
from pydantic import model_validator

class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    resolution_note: str | None = None

    @model_validator(mode="after")
    def note_required_when_resolved(self) -> Self:
        if self.status == TicketStatus.RESOLVED and not self.resolution_note:
            raise ValueError("resolution_note is required when resolving a ticket")
        return self
```

### 7. Serialization: `model_dump` and its options
```python
t = Ticket(status="open")
t.model_dump()                        # {'status': <TicketStatus.OPEN: 'open'>, 'priority': None}
t.model_dump(mode="json")             # {'status': 'open', 'priority': None}  (JSON-safe types)
t.model_dump_json()                   # '{"status":"open","priority":null}'
t.model_dump(exclude_none=True)       # drops None fields
t.model_dump(include={"status"})      # only these
```

**`exclude_unset` matters most for PATCH**:
```python
class TicketUpdate(BaseModel):
    subject: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None

u = TicketUpdate.model_validate({"priority": None})
u.model_dump()                     # {'subject': None, 'status': None, 'priority': None}
u.model_dump(exclude_unset=True)   # {'priority': None}  → "the client explicitly cleared priority"
```
`exclude_unset` tells *"not sent"* apart from *"sent as null"*. In JS you'd check `"priority" in body`.

### 8. Copying with changes (immutability-friendly)
```python
updated = t.model_copy(update={"status": TicketStatus.CLOSED})
```
Note: `model_copy(update=...)` **does not validate** the update values. Only pass trusted or already-validated data.

### 9. Model config
```python
from pydantic import BaseModel, ConfigDict

class StrictIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",          # unknown keys → error (default "ignore" silently drops them)
        str_strip_whitespace=True,
        frozen=True,             # instances are immutable + hashable
    )
    name: str

class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)   # allow reading from ORM objects (M2)
    id: int
    subject: str

# TicketOut.model_validate(orm_ticket) reads orm_ticket.id, orm_ticket.subject
```
`from_attributes=True` (called `orm_mode` in v1) is what lets FastAPI turn SQLAlchemy objects into responses in M2.

### 10. Computed fields and aliases
```python
from pydantic import Field, computed_field

class TicketOut(BaseModel):
    subject: str
    body: str

    @computed_field
    @property
    def preview(self) -> str:
        return self.body[:80]

class ExternalWebhook(BaseModel):
    # Accept camelCase input from a JS service, but use snake_case in Python
    model_config = ConfigDict(populate_by_name=True)
    customer_email: str = Field(alias="customerEmail")
```
For a whole camelCase API, use `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)`
with `from pydantic.alias_generators import to_camel`.

### 11. Sharing fields with a base class
```python
class TicketBase(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=1)

class TicketCreate(TicketBase):
    customer_email: EmailStr

class TicketOut(TicketBase):
    id: UUID
    customer_email: EmailStr
    status: TicketStatus
    priority: TicketPriority | None
    category: str | None
    created_at: datetime
    updated_at: datetime
```

### 12. Settings with `pydantic-settings`
This is already in `app/core/config.py`:
```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TriageDesk"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./triagedesk.db"
    jwt_secret: str = "change-me"
    anthropic_api_key: str = ""

@lru_cache
def get_settings() -> Settings:
    return Settings()
```
- Each field is read from the env var with the same name, **case-insensitive** (`DEBUG=true` → `debug=True`).
- Precedence is: real environment variables > `.env` file > defaults.
- Types are validated at startup. `DEBUG=maybe` crashes immediately with a clear error, which is the behavior you want.
- `@lru_cache` makes `get_settings()` a lazily built singleton (chapter 08). In tests you can
  call `get_settings.cache_clear()` after changing env vars.
- For secrets, `SecretStr` hides the value in logs and reprs (`settings.jwt_secret.get_secret_value()`).

## Gotchas
- **v1 vs v2 APIs.** `.dict()` → `.model_dump()`, `.json()` → `.model_dump_json()`, `parse_obj` →
  `model_validate`, `class Config` → `model_config = ConfigDict(...)`, `@validator` → `@field_validator`,
  `orm_mode` → `from_attributes`. If a snippet uses the left-hand side, it's from v1.
- **Mutable defaults are safe in Pydantic** (`tags: list[str] = []` is copied per instance), unlike
  plain function defaults (chapter 03). `Field(default_factory=list)` is still the explicit style.
- **`Optional` doesn't mean "may be omitted".** `x: str | None` with **no default** is *required*
  (it must be sent, though it may be `null`). For truly optional fields, write `x: str | None = None`.
- **Lax coercion can surprise you.** `int` accepts `"42"` and `4.0` but rejects `4.5`. `str` does
  **not** accept `42`. Use `StrictInt` / `Field(strict=True)` when you need exactness.
- **Default `extra="ignore"`.** A client typo like `{"subjcet": ...}` is silently dropped (and then
  you get "subject missing"). Use `extra="forbid"` on input models if you want loud failures.
- **Validators must `return` the value.** Forget the `return` and the field becomes `None`.
- **Don't forget `@classmethod`** under `@field_validator`, and keep the decorator order shown.
- **Datetimes:** always use timezone-aware values (`datetime.now(UTC)`). Pydantic serializes them as ISO 8601 strings.

## Exercises
1. Write `SignupIn(email: EmailStr, password: str, password_confirm: str)` with a model validator
   that rejects mismatched passwords and a field validator that requires ≥ 8 characters and at least one digit.
2. Given `class P(BaseModel): a: int; b: str | None = None`, what do `P.model_validate({"a": "1"})`,
   `P.model_validate({"a": 1.5})` and `P(a=1).model_dump(exclude_unset=True)` produce?
3. Create a `TicketUpdate` and show the difference between `{}` and `{"category": null}` using
   `model_dump(exclude_unset=True)`.
4. Make a model that accepts `{"customerEmail": "x@y.z"}` but exposes `.customer_email` in Python,
   and serializes back to camelCase with `model_dump(by_alias=True)`.
5. Add a `max_tickets_per_page: int = 50` setting. Override it with an environment variable from the
   shell (`MAX_TICKETS_PER_PAGE=10 uv run python -c ...`) and print it.

<details><summary>Answers</summary>

1. ```python
   class SignupIn(BaseModel):
       email: EmailStr
       password: str
       password_confirm: str

       @field_validator("password")
       @classmethod
       def strong(cls, v: str) -> str:
           if len(v) < 8 or not any(c.isdigit() for c in v):
               raise ValueError("password needs 8+ chars and a digit")
           return v

       @model_validator(mode="after")
       def match(self) -> Self:
           if self.password != self.password_confirm:
               raise ValueError("passwords do not match")
           return self
   ```
2. `P(a=1, b=None)`; a ValidationError (`1.5` has a fractional part); `{'a': 1}`.
3. `TicketUpdate.model_validate({}).model_dump(exclude_unset=True) == {}` and
   `TicketUpdate.model_validate({"category": None}).model_dump(exclude_unset=True) == {"category": None}`.
4. ```python
   from pydantic.alias_generators import to_camel
   class C(BaseModel):
       model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
       customer_email: str
   c = C.model_validate({"customerEmail": "x@y.z"})
   c.customer_email, c.model_dump(by_alias=True)   # ('x@y.z', {'customerEmail': 'x@y.z'})
   ```
5. `MAX_TICKETS_PER_PAGE=10 uv run python -c "from app.core.config import get_settings; print(get_settings().max_tickets_per_page)"` prints `10`.
</details>

## Apply to TriageDesk: M1 (part 2: schemas)
Build the schemas first, then the routes from [chapter 13](13-fastapi-basics.md#apply-to-triagedesk-m1-part-1-routes).

**Goal:** All ticket input/output shapes live in `app/schemas/ticket.py`, and routes import from there.

**Packages:** none new.

**Files**
| File | Contents |
|---|---|
| `app/schemas/__init__.py` | empty |
| `app/schemas/ticket.py` | `TicketStatus`, `TicketPriority` (StrEnums), `TicketBase`, `TicketCreate`, `TicketUpdate`, `TicketOut` |

**Schema spec**
| Model | Fields | Notes |
|---|---|---|
| `TicketStatus` | `open`, `in_progress`, `resolved`, `closed` | `StrEnum` |
| `TicketPriority` | `low`, `medium`, `high`, `urgent` | `StrEnum` |
| `TicketCreate` | `subject` (3–200 chars, stripped), `body` (1–10 000 chars), `customer_email: EmailStr` | `extra="forbid"`, so `id`/`status` can't be injected |
| `TicketUpdate` | `subject?`, `body?`, `status?`, `priority?`, `category?` (all `X \| None = None`) | used with `exclude_unset=True` |
| `TicketOut` | `id: UUID`, `subject`, `body`, `customer_email`, `status`, `priority: TicketPriority \| None`, `category: str \| None`, `created_at`, `updated_at` | `from_attributes=True` (ready for M2) |

**Acceptance criteria**
- [ ] `TicketCreate` rejects a blank or whitespace-only subject, an invalid email and unknown fields
- [ ] Customer email is stored lowercase
- [ ] `TicketUpdate` with `{}` changes nothing. With `{"category": null}` it clears the category.
- [ ] `/docs` shows the enum values as dropdowns for `status`/`priority`
- [ ] A small unit test file `tests/test_schemas.py` exercises the validators directly (no HTTP)
- [ ] Routes (chapter 13) use these models, and the M1 checklist there passes

**Hints**
- `str_strip_whitespace=True` in `model_config` strips all string fields, so you may not need a validator for that.
- `customer_email` lowercasing: a `mode="before"` field validator, or `mode="after"` on the `str` value.
- Keep `TicketOut` free of anything secret. Later you might add `internal_notes`, which customers must never see.

<details><summary>Reference sketch (peek only after trying)</summary>

```python
# app/schemas/ticket.py (partial)
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=1, max_length=10_000)
    customer_email: EmailStr

    @field_validator("customer_email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject: str
    # ... remaining fields ...
    created_at: datetime
    updated_at: datetime
```
</details>
