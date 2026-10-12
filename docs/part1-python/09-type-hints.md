# 09 · Type hints

## Concept
Python is dynamically typed, but since 3.5 it supports optional **type hints**:
```python
def assign(ticket_id: int, agent: str | None = None) -> bool: ...
```
There are two ideas to hold at once:
1. **The Python interpreter ignores hints at runtime.** `assign("oops")` runs fine. Hints are
   metadata stored in `__annotations__`.
2. **Tools use them.** A *type checker* (pyright, which powers VS Code's Pylance, or mypy) checks them
   statically like `tsc`, and **libraries read them at runtime to do real work.** FastAPI and Pydantic
   use your hints to validate requests, convert types and generate OpenAPI docs. In this stack, type
   hints aren't decoration. They're the API.

The project convention (see `CLAUDE.md`) is type hints on every function signature.

## In Node you'd…
| TypeScript | Python |
|---|---|
| `let x: number` | `x: int` / `x: float` |
| `string`, `boolean` | `str`, `bool` |
| `string[]` / `Array<string>` | `list[str]` |
| `[string, number]` (tuple) | `tuple[str, int]`; `tuple[int, ...]` for variable length |
| `Record<string, number>` | `dict[str, int]` |
| `Set<string>` | `set[str]` |
| `string \| null` | `str \| None` (older code: `Optional[str]`) |
| `any` | `Any` (escape hatch, avoid) |
| `unknown` | `object` |
| `"low" \| "high"` (literal union) | `Literal["low", "high"]` |
| `interface` / object type | `TypedDict` (dict shape), `@dataclass` / Pydantic model (objects), `Protocol` (structural) |
| `function f<T>(x: T): T` | `def f[T](x: T) -> T:` (3.12 syntax) |
| `(a: number) => string` | `Callable[[int], str]` |
| `type Id = string` | `type TicketId = str` (3.12) |
| `void` | `-> None` |
| `never` | `NoReturn` / `Never` |
| `readonly` / `as const` | `Final`, `frozen=True` dataclasses |
| `tsc --noEmit` | `pyright` or `mypy` |

Key differences:
- **There's no compile step.** Type errors don't stop your program. You have to *run* the checker (or watch your editor).
- **Nominal by default, structural when asked.** Classes are nominal (you must inherit), but `Protocol` gives you TS-style structural ("duck") typing.
- **Runtime validation is opt-in** via Pydantic (chapter 14). It's like having Zod derived from your types automatically.

## Examples

### Basics
```python
priority: str = "high"
retries: int = 3
score: float = 0.87
is_urgent: bool = False

def summarize(text: str, max_words: int = 50) -> str:
    return " ".join(text.split()[:max_words])

def log(msg: str) -> None:     # returns nothing
    print(msg)
```

### Collections (lowercase built-ins since 3.9)
```python
tags: list[str] = ["billing", "refund"]
counts: dict[str, int] = {"billing": 3}
pair: tuple[str, float] = ("billing", 0.92)
ids: tuple[int, ...] = (1, 2, 3)
unique: set[int] = {1, 2}
matrix: list[list[float]] = [[0.1, 0.2], [0.3, 0.4]]   # e.g. embeddings
```
In parameters, prefer the *abstract* types from `collections.abc`, so callers can pass any compatible
type (accept broad, return specific):
```python
from collections.abc import Iterable, Sequence, Mapping, Iterator

def total_length(texts: Iterable[str]) -> int:      # accepts list, tuple, generator, set…
    return sum(len(t) for t in texts)
```

### Optional and unions
```python
def find_agent(name: str) -> dict | None:   # may return None
    ...

agent = find_agent("ana")
agent["email"]          # ❌ pyright: "agent" is possibly None
if agent is not None:
    agent["email"]      # ✅ narrowed, just like TS control-flow narrowing

def parse_id(raw: str | int) -> int:
    if isinstance(raw, str):     # isinstance narrows like typeof
        return int(raw)
    return raw
```
`Optional[X]` (from `typing`) means exactly `X | None`. You'll see it in older code.

### Literal: string enums without the ceremony
```python
from typing import Literal

Priority = Literal["low", "medium", "high", "urgent"]

def set_priority(ticket_id: int, priority: Priority) -> None: ...

set_priority(1, "high")      # ✅
set_priority(1, "asap")      # ❌ type checker error (and Pydantic rejects it at runtime)
```
`Enum` (chapter 06) is the alternative when you want a real runtime object with members.

### Type aliases
```python
type TicketId = int                       # 3.12 syntax
type Embedding = list[float]
type Scores = dict[str, float]

def nearest(query: Embedding, k: int = 5) -> list[tuple[TicketId, float]]: ...
```

### TypedDict: the shape of a dict (like a TS interface for JSON)
```python
from typing import TypedDict, NotRequired

class TicketDict(TypedDict):
    id: int
    title: str
    priority: Priority
    assignee: NotRequired[str]     # key may be missing (like `assignee?: string`)

t: TicketDict = {"id": 1, "title": "Login broken", "priority": "high"}
t["priorty"]                       # ❌ typo caught by the checker
```
It's still a plain dict at runtime, with no validation. Use it for typing JSON you got from somewhere
else (e.g. an API response). For data you own, prefer dataclasses or Pydantic models.

### Generics (3.12 syntax)
```python
def first[T](items: list[T]) -> T | None:
    return items[0] if items else None

first([1, 2])        # inferred: int | None
first(["a"])         # inferred: str | None

class Page[T]:                       # generic class, like class Page<T>
    def __init__(self, items: list[T], total: int) -> None:
        self.items = items
        self.total = total

page: Page[TicketDict] = Page([t], total=1)

def clamp[N: (int, float)](x: N, lo: N, hi: N) -> N:   # constrained: int or float
    return max(lo, min(x, hi))
```
In older code (and many libraries) you'll see `T = TypeVar("T")` and `class Page(Generic[T])`. It means the same thing.

### Callable
```python
from collections.abc import Callable

Classifier = Callable[[str], str]            # takes str, returns str

def run_all(texts: list[str], classify: Classifier) -> list[str]:
    return [classify(t) for t in texts]

run_all(["refund"], lambda t: "billing")
```

### Protocol: structural typing (TS-style interfaces)
This is how you describe "anything with a `.complete()` method" without inheritance. It's perfect for
swapping a real LLM client with a fake one in tests:
```python
from typing import Protocol

class LLMClient(Protocol):
    def complete(self, prompt: str) -> str: ...

class ClaudeClient:                         # does NOT inherit LLMClient
    def complete(self, prompt: str) -> str:
        return "real answer"

class FakeLLM:
    def complete(self, prompt: str) -> str:
        return "canned answer"

def draft_reply(llm: LLMClient, ticket: str) -> str:
    return llm.complete(f"Reply to: {ticket}")

draft_reply(ClaudeClient(), "help")   # ✅
draft_reply(FakeLLM(), "help")        # ✅ structural match
```

### Annotated: attaching metadata (you'll see it everywhere in FastAPI)
`Annotated[T, extra]` means "the type is T, and here's extra info for whichever library cares":
```python
from typing import Annotated
from fastapi import Query, Depends

def list_tickets(
    session: Annotated[AsyncSession, Depends(get_session)],  # AsyncSession + "inject this"
    limit: Annotated[int, Query(ge=1, le=100)] = 20,        # int + validation rules
): ...
```
Type checkers see `int`, and FastAPI reads the `Query(...)` metadata. Chapters 13 and 16 cover this.

### Other useful bits
```python
from typing import Any, Final, Self, cast, TYPE_CHECKING

MAX_RETRIES: Final = 3                 # constant, can't be reassigned (checker-enforced)

class Builder:
    def with_title(self, t: str) -> Self:   # returns the same class (works for subclasses)
        self.title = t
        return self

data: Any = json.loads(raw)            # escape hatch: the checker stops checking
ticket = cast(TicketDict, data)        # "trust me" (like TS `as`), no runtime effect

if TYPE_CHECKING:                      # imports only for the type checker (avoids circular imports)
    from app.models.user import User
```
Forward references: `def parent(self) -> "Ticket":` (in quotes) when a class refers to itself before
it's fully defined. On 3.12, `Self` usually reads better.

### Running a type checker
Pylance in VS Code already checks as you type. To check from the CLI (optional):
```bash
uv add --dev pyright
uv run pyright app
```
Set Pylance's `python.analysis.typeCheckingMode` to `"standard"` to get TS-`strict`-ish feedback.

### Hints at runtime (how FastAPI does its magic)
```python
import typing
def f(ticket_id: int, q: str | None = None) -> bool: ...
typing.get_type_hints(f)
# {'ticket_id': <class 'int'>, 'q': str | None, 'return': <class 'bool'>}
```
FastAPI calls something like this on your route function and builds a validator for each parameter.

## Gotchas
- **Hints aren't enforced.** `def f(x: int)` happily accepts `"5"`. If you need validation, use Pydantic (or FastAPI, which uses Pydantic).
- **`list[str]` vs `List[str]`.** `typing.List`, `Dict`, `Optional` and `Union` are older spellings. Use the lowercase built-ins and `|`. Ruff's `UP` rules rewrite the old forms automatically.
- **The mutable default problem doesn't go away with hints.** `def f(tags: list[str] = [])` is still a bug (chapter 03). Use `tags: list[str] | None = None`.
- **`float` accepts `int`** (int is treated as compatible), but `int` doesn't accept `float`.
- **`dict` returned from `json.loads` is `Any`.** Validate it (Pydantic) or `cast` it. Don't pretend it's typed.
- **`Any` is contagious**, just like `any` in TS. One `Any` silences checking for everything that touches it.

## Exercises
Starter file: `exercises/ch09_types.py`. Here you add hints *and* make the asserts pass. Then run
`uv add --dev pyright && uv run pyright exercises/ch09_types.py` (optional) and aim for 0 errors.
The solution is in `exercises/solutions/ch09_types.py`.

1. Write a `Priority` Literal alias and a `TicketDict` TypedDict (`id`, `title`, `priority`, optional `tags`).
2. `first[T]`: a generic function returning the first item or `None`.
3. `by_priority(tickets, priority) -> list[TicketDict]`: filter tickets.
4. A `Notifier` Protocol with `send(to: str, message: str) -> bool`, plus a `FakeNotifier` that records messages, and `notify_all(notifier, tickets) -> int` that returns how many sends succeeded.

<details><summary>Answers</summary>

```python
from typing import Literal, NotRequired, Protocol, TypedDict

type Priority = Literal["low", "medium", "high", "urgent"]

class TicketDict(TypedDict):
    id: int
    title: str
    priority: Priority
    tags: NotRequired[list[str]]

def first[T](items: list[T]) -> T | None:
    return items[0] if items else None

def by_priority(tickets: list[TicketDict], priority: Priority) -> list[TicketDict]:
    return [t for t in tickets if t["priority"] == priority]

class Notifier(Protocol):
    def send(self, to: str, message: str) -> bool: ...

class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
    def send(self, to: str, message: str) -> bool:
        self.sent.append((to, message))
        return True

def notify_all(notifier: Notifier, tickets: list[TicketDict]) -> int:
    return sum(notifier.send("agents", f"#{t['id']}: {t['title']}") for t in tickets)
```
`sum()` over bools works because `True == 1`.
</details>

## Apply to TriageDesk: everywhere
- Open `app/core/config.py`. The class attributes are type hints (`debug: bool = False`), and
  pydantic-settings uses them to **convert** `DEBUG=true` from `.env` (a string) into a real `bool`.
- Open `app/api/routes/health.py`. The `-> dict[str, str]` return hint tells FastAPI what the response looks like.
- From M1 on, **every** function you write gets hints. In M6 you'll define an `LLMClient`-style
  Protocol (or wrap the SDK in `app/ai/llm.py`) so tests can swap in a fake, exactly like the
  `FakeLLM` example above.
