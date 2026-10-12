# 05 · Errors & exceptions

## Concept
Python uses exceptions for error handling everywhere. The standard library and every major framework
**raise** rather than returning error codes or `null`. Python culture also prefers **EAFP**: "Easier
to Ask Forgiveness than Permission". You try the operation and catch the specific failure, instead of
checking every precondition first (LBYL, "Look Before You Leap").

Exceptions are classes arranged in a hierarchy, and `except SomeError` also catches its subclasses.
That lets you design your own hierarchy (`TriageDeskError → NotFoundError → TicketNotFoundError`)
and handle errors at the right level of abstraction. In M3 a FastAPI exception handler will
turn these into HTTP responses.

## In Node you'd…
```js
class TicketNotFoundError extends Error {
  constructor(id) {
    super(`Ticket ${id} not found`);
    this.name = "TicketNotFoundError";
    this.ticketId = id;
  }
}

try {
  const t = getTicket(42);
} catch (err) {
  if (err instanceof TicketNotFoundError) {
    res.status(404).json({ error: err.message });
  } else {
    throw err;
  }
} finally {
  release();
}
```
```python
class TicketNotFoundError(Exception):
    def __init__(self, ticket_id: int) -> None:
        super().__init__(f"Ticket {ticket_id} not found")
        self.ticket_id = ticket_id

try:
    t = get_ticket(42)
except TicketNotFoundError as err:          # type-based dispatch is built in
    print(f"404: {err}")
finally:
    release()
```
Differences from JS:
- You **catch by type** with multiple `except` clauses, so there's no `instanceof` chain inside one `catch`.
- `try` has an **`else`** clause, which runs only if no exception occurred.
- Uncaught exceptions print a **traceback** (read it bottom-up: the last line is the error, and the lines above are the call stack).
- In JS you can `throw "a string"`. Python only allows `BaseException` subclasses.

## Examples

### Full try statement
```python
import json

def load_ticket(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"bad JSON at pos {e.pos}: {e.msg}")
        raise                                   # re-raise the SAME exception (keeps the traceback)
    except (TypeError, ValueError):             # several types at once
        raise
    else:
        print("parsed ok")                      # only when no exception was raised
        return data
    finally:
        print("always runs")                    # cleanup, even on return/raise
```
Keep the `try` body **small**, wrapping only the line that can fail. Code that should only run on success goes in `else`.

### Built-in exceptions you'll meet constantly
```
BaseException
 ├── KeyboardInterrupt, SystemExit      ← don't catch these
 └── Exception                          ← catch from here down
      ├── ValueError        int("abc"), bad value of the right type
      ├── TypeError         "1" + 1, wrong number of args
      ├── KeyError          d["missing"]
      ├── IndexError        lst[99]
      ├── AttributeError    None.title
      ├── LookupError       (parent of KeyError & IndexError)
      ├── FileNotFoundError (an OSError)
      ├── TimeoutError, ConnectionError
      ├── NotImplementedError
      └── RuntimeError
```
`AttributeError: 'NoneType' object has no attribute 'x'` is Python's version of
`Cannot read properties of undefined`.

### Raising
```python
def set_priority(p: int) -> None:
    if not 1 <= p <= 4:
        raise ValueError(f"priority must be 1-4, got {p}")
```

### Chaining: `raise … from …`
When you translate a low-level error into a domain error, keep the cause:
```python
class KnowledgeBaseError(Exception): ...

def read_article(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError as e:
        raise KnowledgeBaseError(f"article missing: {path}") from e
```
The traceback then shows both errors, joined by *"The above exception was the direct cause of…"*.
Use `from None` to hide the original deliberately. JS has the equivalent `new Error(msg, { cause })`.

### Designing a domain exception hierarchy (preview of M3)
```python
class TriageDeskError(Exception):
    """Base for all app errors. Handlers can catch this one type."""
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(TriageDeskError):
    status_code = 404
    code = "not_found"


class TicketNotFoundError(NotFoundError):
    code = "ticket_not_found"

    def __init__(self, ticket_id: int) -> None:
        super().__init__(f"Ticket {ticket_id} not found")
        self.ticket_id = ticket_id


class PermissionDeniedError(TriageDeskError):
    status_code = 403
    code = "permission_denied"
```
```python
try:
    raise TicketNotFoundError(42)
except NotFoundError as e:                   # catches the subclass too
    print(e.status_code, e.code, e.message)  # 404 ticket_not_found Ticket 42 not found
```
Services raise these domain errors and know nothing about HTTP. One FastAPI exception handler maps
`TriageDeskError` to `{"error": {"code": ..., "message": ...}}` with `status_code`.
Express users will recognise this as the error-handling middleware pattern.

### EAFP vs LBYL
```python
# LBYL (JS-style)
if "priority" in data and isinstance(data["priority"], int):
    p = data["priority"]
else:
    p = 2

# EAFP (Pythonic)
try:
    p = int(data["priority"])
except (KeyError, ValueError, TypeError):
    p = 2

# …or, for the simple case, just: p = data.get("priority", 2)
```

### Suppressing and grouping
```python
from contextlib import suppress

with suppress(FileNotFoundError):         # "ignore this specific error"
    os.remove("tmp.lock")
```
Python 3.11 added `ExceptionGroup` and `except*` for raising several errors at once (for example from
concurrent tasks, which is roughly the `Promise.allSettled` situation). You'll see these in chapter 11 with `asyncio.TaskGroup`.

### Adding context: notes (3.11+)
```python
try:
    process(ticket)
except ValueError as e:
    e.add_note(f"while processing ticket {ticket.id}")
    raise
```

### Assertions
`assert cond, "msg"` raises `AssertionError`. Use it in tests and for internal invariants, **never
for validating user input**, because `python -O` strips asserts.

## Gotchas
- **Never use a bare `except:` or `except Exception: pass`.** They swallow bugs (and bare `except` even catches Ctrl-C). Catch specific types.
- **`raise` alone re-raises with the original traceback.** `raise e` works but adds noise; `raise New() from e` translates.
- **A `return` in `finally` overrides** the try block's return or exception. Don't do that.
- **Huge `try` blocks** hide which line actually failed. Keep them narrow.
- **Exception messages** come from `str(e)`. Don't rely on `e.args[0]` formatting; store structured fields (like `ticket_id`).
- **Python has no checked exceptions.** Document what a function raises in its docstring.
- **`except A, B:`** is Python 2 syntax and an error now. Write `except (A, B):`.

## Exercises
Starter file: `exercises/ch05_errors.py`. Run `uv run python exercises/ch05_errors.py`.

1. Build the hierarchy: `TriageDeskError` (status 500) → `NotFoundError` (404) → `TicketNotFoundError(ticket_id)`,
   and `ValidationError` (422).
2. `get_ticket(store, ticket_id)` raises `TicketNotFoundError` (translating the `KeyError` with `from`).
3. `parse_priority(value)` accepts `int` or numeric `str` in 1–4, and otherwise raises `ValidationError` (chain the `ValueError`).
4. `to_error_response(exc)` → `(status_code, {"error": {"code": ..., "message": ...}})`. This is exactly what the M3 handler will do.
5. `safe_parse_priority(value, default=2)`: EAFP wrapper that returns the default on `ValidationError`.

<details><summary>Answers</summary>

```python
class TriageDeskError(Exception):
    status_code = 500
    code = "internal_error"
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

class NotFoundError(TriageDeskError):
    status_code, code = 404, "not_found"

class TicketNotFoundError(NotFoundError):
    code = "ticket_not_found"
    def __init__(self, ticket_id: int) -> None:
        super().__init__(f"Ticket {ticket_id} not found")
        self.ticket_id = ticket_id

class ValidationError(TriageDeskError):
    status_code, code = 422, "validation_error"

def get_ticket(store, ticket_id):
    try:
        return store[ticket_id]
    except KeyError as e:
        raise TicketNotFoundError(ticket_id) from e

def parse_priority(value):
    try:
        p = int(value)
    except (TypeError, ValueError) as e:
        raise ValidationError(f"priority must be a number, got {value!r}") from e
    if not 1 <= p <= 4:
        raise ValidationError(f"priority must be 1-4, got {p}")
    return p

def to_error_response(exc):
    return exc.status_code, {"error": {"code": exc.code, "message": exc.message}}

def safe_parse_priority(value, default=2):
    try:
        return parse_priority(value)
    except ValidationError:
        return default
```
</details>

## Apply to TriageDesk: M3 preview
In **M3** you'll create `app/core/errors.py` with this hierarchy, raise `TicketNotFoundError` from the
ticket service, and register one handler in `create_app()`:
```python
@app.exception_handler(TriageDeskError)
async def handle_app_error(request: Request, exc: TriageDeskError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": exc.code, "message": exc.message}})
```
Your exercise 4 solution is the core of that handler. Keep it.
