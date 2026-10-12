# 06 · Classes, dataclasses, enums

## Concept
Python classes are like JS classes, with some differences:
- `__init__` is the constructor, and **`self` is explicit**: it's the first parameter of every method.
- Attributes are usually created in `__init__` by assigning to `self.x`. There are no field declarations
  (unless you use `@dataclass` or Pydantic, which read class-level type hints).
- **Dunder ("double underscore") methods** like `__repr__`, `__eq__`, `__len__` and `__lt__` hook your
  objects into language features (printing, `==`, `len()`, sorting, `in`, `with`, iteration…). This
  is how Python does "operator overloading" and protocols.
- There are no real private fields. `_name` means "internal, please don't touch" and `__name` gets
  name-mangled. Python relies on convention ("we're all consenting adults").
- **`@dataclass`** generates `__init__`, `__repr__` and `__eq__` for you. It's the go-to for plain data
  objects. **`Enum` / `StrEnum`** give you real enums (TS `enum` / string-literal unions).

In TriageDesk you'll mostly write **Pydantic models** (chapter 14) and **SQLAlchemy models**
(chapter 15). Both are classes built on these exact ideas, so this chapter makes them feel natural.

## In Node you'd…
```ts
enum Priority { Low = "low", High = "high" }

class Ticket {
  static count = 0;
  #secret = "x";                       // truly private
  constructor(public id: number, public title: string,
              public priority: Priority = Priority.Low, public tags: string[] = []) {
    Ticket.count++;
  }
  get isUrgent(): boolean { return this.priority === Priority.High; }
  toString() { return `Ticket(${this.id})`; }
  static fromJSON(o: any) { return new Ticket(o.id, o.title); }
}
```
```python
from dataclasses import dataclass, field
from enum import StrEnum

class Priority(StrEnum):
    LOW = "low"
    HIGH = "high"

@dataclass
class Ticket:
    id: int
    title: str
    priority: Priority = Priority.LOW
    tags: list[str] = field(default_factory=list)   # never `= []` (chapter 03)

    @property
    def is_urgent(self) -> bool:
        return self.priority is Priority.HIGH

    @classmethod
    def from_dict(cls, d: dict) -> "Ticket":
        return cls(id=d["id"], title=d["title"])

t = Ticket(1, "Refund", Priority.HIGH)
print(t)            # Ticket(id=1, title='Refund', priority=<Priority.HIGH: 'high'>, tags=[])
t.is_urgent         # True (a property, so no parentheses)
```

## Examples

### A plain class
```python
class TicketQueue:
    """FIFO queue of ticket ids for one support agent."""

    max_size = 100                      # class attribute: shared by all instances (like static)

    def __init__(self, agent: str) -> None:
        self.agent = agent              # instance attributes
        self._items: list[int] = []     # "internal" by convention

    def push(self, ticket_id: int) -> None:
        if len(self._items) >= self.max_size:
            raise OverflowError("queue full")
        self._items.append(ticket_id)

    def pop(self) -> int:
        return self._items.pop(0)

    # dunders: plug into Python syntax
    def __len__(self) -> int:                 # len(q)
        return len(self._items)

    def __contains__(self, ticket_id: int) -> bool:   # 7 in q
        return ticket_id in self._items

    def __iter__(self):                       # for tid in q
        return iter(self._items)

    def __repr__(self) -> str:                # what the REPL/debugger shows
        return f"TicketQueue(agent={self.agent!r}, size={len(self)})"

q = TicketQueue("ana")
q.push(7); q.push(9)
len(q), 7 in q, list(q), q          # (2, True, [7, 9], TicketQueue(agent='ana', size=2))
```
`q.push(7)` is sugar for `TicketQueue.push(q, 7)`. That's where `self` comes from. There's no
`this` rebinding confusion, because methods are always bound to their instance.

### `__repr__` vs `__str__`
- `__repr__`: an unambiguous developer view (REPL, logs, debugger). **Always define it** on your own classes.
- `__str__`: the friendly view used by `print()` and `f"{x}"`. It falls back to `__repr__`.

### Common dunders
| Dunder | Triggered by | JS analogy |
|---|---|---|
| `__init__` | `Cls(...)` | `constructor` |
| `__repr__` / `__str__` | `repr(x)` / `str(x)`, `print` | `toString`, `util.inspect.custom` |
| `__eq__` / `__hash__` | `==`, dict keys / set members | — |
| `__lt__` etc. | `<`, `sorted()` | — |
| `__len__`, `__contains__`, `__iter__`, `__getitem__` | `len`, `in`, `for`, `x[k]` | `Symbol.iterator` |
| `__call__` | `x()` | — |
| `__enter__` / `__exit__` | `with x:` (chapter 07) | `using` (TC39) |
| `__bool__` | `if x:` | — |

### Inheritance & `super()`
```python
class Notifier:
    def __init__(self, sender: str) -> None:
        self.sender = sender

    def send(self, to: str, message: str) -> str:
        raise NotImplementedError

class EmailNotifier(Notifier):
    def __init__(self, sender: str, smtp_host: str) -> None:
        super().__init__(sender)          # call the parent constructor
        self.smtp_host = smtp_host

    def send(self, to: str, message: str) -> str:
        return f"[email via {self.smtp_host}] {self.sender} → {to}: {message}"

isinstance(EmailNotifier("a", "h"), Notifier)   # True
```
For "interfaces", Python uses `abc.ABC` + `@abstractmethod` (nominal) or `typing.Protocol`
(structural, like TS interfaces, covered in chapter 09):
```python
from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str: ...

# LLMClient()  → TypeError: Can't instantiate abstract class
```
Python supports multiple inheritance (`class A(B, C)`), but app code rarely needs it. Prefer
**composition**: pass collaborators in.
```python
class TriageService:
    def __init__(self, llm: LLMClient, notifier: Notifier) -> None:   # composition + DI
        self.llm = llm
        self.notifier = notifier
```
This is the pattern behind M3 and M6. In tests you pass a fake `LLMClient`.

### `@property`: computed attributes and validated setters
```python
class SLA:
    def __init__(self, hours: int) -> None:
        self.hours = hours                  # goes through the setter below

    @property
    def hours(self) -> int:
        return self._hours

    @hours.setter
    def hours(self, value: int) -> None:
        if value <= 0:
            raise ValueError("hours must be positive")
        self._hours = value

    @property
    def minutes(self) -> int:               # read-only computed
        return self._hours * 60
```
Start with plain attributes. You can switch to a property later without changing callers, which is
why Python doesn't need Java-style getters and setters.

### `@classmethod` and `@staticmethod`
```python
class Ticket:
    def __init__(self, title: str, priority: int) -> None:
        self.title, self.priority = title, priority

    @classmethod
    def urgent(cls, title: str) -> "Ticket":     # alternative constructor; cls = the class
        return cls(title, priority=4)

    @staticmethod
    def is_valid_priority(p: int) -> bool:       # namespaced plain function, no self/cls
        return 1 <= p <= 4
```
`classmethod` is the idiomatic factory (`datetime.fromisoformat`, `Model.model_validate` in Pydantic).
It works correctly with subclasses because `cls` is whatever class it was called on.

### `@dataclass` in depth
```python
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime, UTC

@dataclass(slots=True)
class Ticket:
    id: int
    title: str
    priority: int = 2
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    internal_note: str = field(default="", repr=False)    # hide from repr

    def __post_init__(self) -> None:                       # validation after generated __init__
        if not 1 <= self.priority <= 4:
            raise ValueError("priority must be 1-4")

t = Ticket(1, "Refund", tags=["billing"])
asdict(t)                         # → dict (recursively), handy for JSON
replace(t, priority=4)            # copy with changes (like {...t, priority: 4})
t == Ticket(1, "Refund", tags=["billing"], created_at=t.created_at)   # True: generated __eq__

@dataclass(frozen=True)           # immutable + hashable → usable as dict key / in sets
class ChunkRef:
    article_id: int
    chunk_index: int
```
Rules: fields without defaults must come before fields with defaults. `slots=True` uses less memory
and blocks typos like `t.titel = …`. `order=True` generates `<`, `>` and the rest, comparing fields in order.

**Dataclass vs Pydantic:** dataclasses **don't validate types** (`Ticket(id="x", title=5)` happily
works). Pydantic models (chapter 14) validate and coerce, which is why we use Pydantic at API
boundaries and dataclasses for internal values.

### Enums
```python
from enum import Enum, IntEnum, StrEnum, auto

class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

TicketStatus.OPEN                   # <TicketStatus.OPEN: 'open'>
TicketStatus("open")                # lookup by value → TicketStatus.OPEN (ValueError if invalid)
TicketStatus["OPEN"]                # lookup by name
TicketStatus.OPEN == "open"         # True: StrEnum members ARE strings, so they serialise to JSON nicely
[s.value for s in TicketStatus]     # ['open', 'in_progress', 'resolved', 'closed']
TicketStatus.OPEN in TicketStatus   # True

class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

Priority.HIGH > Priority.LOW        # True: IntEnum compares like ints
```
Use `StrEnum` for anything that goes into JSON or a DB column (status, category), and `IntEnum` when
ordering matters. FastAPI and Pydantic understand both and show them as enums in `/docs`.

Enums can carry behaviour too:
```python
class TicketStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"

    @property
    def is_terminal(self) -> bool:
        return self in {TicketStatus.RESOLVED, TicketStatus.CLOSED}
```

## Gotchas
- **Forgetting `self`** in a method definition gives `TypeError: takes 0 positional arguments but 1 was given`.
- **Mutable class attributes are shared** by all instances. `class A: items = []` is the mutable-default bug again. Put per-instance state in `__init__`.
- **`@dataclass` fields with `= []`** raise `ValueError: mutable default`. Use `field(default_factory=list)`.
- **Dataclasses don't validate types.** Use Pydantic when data comes from outside.
- **Defining `__eq__` makes the class unhashable** unless you also define `__hash__` (or use `frozen=True`).
- **Compare enum members with `is` or `==`**, and don't compare `.name` strings. `StrEnum` == plain string works, but plain `Enum` doesn't.
- **There's no method overloading.** A second `def` with the same name replaces the first. Use default args or `classmethod` factories.
- **Calling a property:** `t.is_urgent()` raises `TypeError: 'bool' object is not callable`.

## Exercises
Starter file: `exercises/ch06_oop.py`. Run `uv run python exercises/ch06_oop.py`.

These exercises are **M1 prep**: you're modelling the core TriageDesk domain.
1. `TicketStatus(StrEnum)`: open / in_progress / resolved / closed, with an `is_terminal` property.
2. `Priority(IntEnum)`: LOW=1 … URGENT=4.
3. `@dataclass Ticket`: `id`, `title`, `description`, `status=OPEN`, `priority=MEDIUM`, `tags` (default empty list),
   `created_at` (default now, UTC). Validate in `__post_init__` that `title` isn't blank.
4. `Ticket.close()` sets status to CLOSED, but raises `ValueError` if the ticket is already terminal.
5. `Ticket.is_overdue(now, sla_hours)`: True if not terminal and older than the SLA.
6. `TicketStore`: an in-memory store with `add(title, description, priority=...) -> Ticket` (auto-increment id),
   `get(id)` (raises `KeyError`), `list_tickets(status=None)`, plus `__len__` and `__contains__`.

<details><summary>Answers</summary>

See `exercises/solutions/ch06_oop.py` for the full version. The key parts:
```python
class TicketStatus(StrEnum):
    OPEN = "open"; IN_PROGRESS = "in_progress"; RESOLVED = "resolved"; CLOSED = "closed"

    @property
    def is_terminal(self) -> bool:
        return self in (TicketStatus.RESOLVED, TicketStatus.CLOSED)

@dataclass
class Ticket:
    id: int
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: Priority = Priority.MEDIUM
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title must not be blank")

    def close(self) -> None:
        if self.status.is_terminal:
            raise ValueError(f"ticket {self.id} is already {self.status}")
        self.status = TicketStatus.CLOSED

    def is_overdue(self, now: datetime, sla_hours: int) -> bool:
        return not self.status.is_terminal and now - self.created_at > timedelta(hours=sla_hours)

class TicketStore:
    def __init__(self) -> None:
        self._tickets: dict[int, Ticket] = {}
        self._next_id = 1

    def add(self, title, description, priority=Priority.MEDIUM) -> Ticket:
        ticket = Ticket(self._next_id, title, description, priority=priority)
        self._tickets[ticket.id] = ticket
        self._next_id += 1
        return ticket

    def get(self, ticket_id: int) -> Ticket:
        return self._tickets[ticket_id]

    def list_tickets(self, status=None) -> list[Ticket]:
        return [t for t in self._tickets.values() if status is None or t.status == status]

    def __len__(self) -> int: return len(self._tickets)
    def __contains__(self, ticket_id: object) -> bool: return ticket_id in self._tickets
```
(Why `list_tickets` and not `list`? Inside a class body, a method named `list` would shadow the built-in
`list` for any annotation written *after* it, so `-> list[Ticket]` would break.)
</details>

## Apply to TriageDesk: M1 prep
In **M1** (after chapters 13–14) you'll build tickets CRUD. Your `TicketStatus` and `Priority` enums
move almost unchanged into the app, and your `TicketStore` becomes the in-memory repository behind the
`/tickets` routes. The dataclass gets replaced by **Pydantic** schemas (`TicketCreate`, `TicketRead`),
because API input must be validated. Keep your exercise solution open when you start M1.
