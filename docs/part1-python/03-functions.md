# 03 · Functions, arguments, closures, scope

## Concept
Functions are defined with `def`, and they're first-class objects: you can pass them around, store them
in dicts, and return them, just like in JS. What Python adds is a much richer **argument system**:
positional and keyword arguments, defaults, `*args`, `**kwargs`, and keyword-only / positional-only
parameters. Libraries like FastAPI, Pydantic and SQLAlchemy lean on keyword arguments heavily, so get
fluent with them.

## In Node you'd…
```js
function createTicket(title, { priority = 2, tags = [] } = {}) {
  return { title, priority, tags };
}
createTicket("Refund", { priority: 3 });

const log = (...args) => console.log(...args);
const double = x => x * 2;
```
```python
def create_ticket(title: str, *, priority: int = 2, tags: list[str] | None = None) -> dict:
    return {"title": title, "priority": priority, "tags": tags or []}

create_ticket("Refund", priority=3)            # keyword argument, no options object needed

def log(*args, **kwargs):
    print(*args, **kwargs)

double = lambda x: x * 2                       # single-expression only, so prefer def
```
JS imitates named arguments with an options object and destructuring. Python has them built in, and
the `*` makes everything after it **keyword-only** (callers must write `priority=3`).

## Examples

### Positional, keyword, defaults
```python
def assign(ticket_id: int, agent: str, notify: bool = True) -> str:
    return f"{ticket_id}->{agent} notify={notify}"

assign(1, "ana")                       # positional
assign(1, agent="ana", notify=False)   # keyword (any order after the positionals)
assign(agent="ana", ticket_id=1)       # all keyword
# assign(ticket_id=1, "ana")           # SyntaxError: positional after keyword
```
Functions with no `return` return `None` (JS returns `undefined`).

### `*args` and `**kwargs`
`*args` collects extra positionals into a **tuple**, and `**kwargs` collects extra keywords into a **dict**.
```python
def audit(event: str, *args: object, **kwargs: object) -> None:
    print(event, args, kwargs)

audit("ticket.updated", 42, "ana", field="priority", old=2, new=3)
# ticket.updated (42, 'ana') {'field': 'priority', 'old': 2, 'new': 3}
```
The same `*`/`**` **unpack** at the call site (JS spread):
```python
params = {"agent": "ana", "notify": False}
assign(7, **params)                    # assign(7, agent="ana", notify=False)
args = [7, "bo"]
assign(*args)
```

### Keyword-only and positional-only parameters
```python
def search(query: str, /, *, limit: int = 10, category: str | None = None) -> list[str]:
    ...
#          ^ before "/" = positional-only  ^ after "*" = keyword-only
search("refund", limit=5)       # ok
# search(query="refund")        # TypeError (positional-only)
# search("refund", 5)           # TypeError (limit is keyword-only)
```
Keyword-only args (`*`) are the most useful of these. They make call sites self-documenting and let
you add parameters later without breaking callers. Positional-only (`/`) is rare in app code.

Full order: `def f(pos_only, /, normal, *args, kw_only, **kwargs)`.

### The mutable default argument trap ⚠️
Default values are evaluated **once, when the `def` runs**, not on every call:
```python
def add_tag(tag: str, tags: list[str] = []) -> list[str]:   # BUG
    tags.append(tag)
    return tags

add_tag("a")   # ['a']
add_tag("b")   # ['a', 'b']   ← the same list is shared across calls!
```
The fix is to use `None` as a sentinel:
```python
def add_tag(tag: str, tags: list[str] | None = None) -> list[str]:
    if tags is None:
        tags = []
    tags.append(tag)
    return tags
```
Ruff rule `B006` catches this. Pydantic and dataclasses use `default_factory=list` for the same reason (chapter 06).

### Functions are objects
```python
def low(t): return t["priority"] <= 2
def high(t): return t["priority"] >= 3

FILTERS = {"low": low, "high": high}        # dispatch table
selected = [t for t in tickets if FILTERS["high"](t)]

sorted(tickets, key=lambda t: t["created_at"])   # lambdas are mostly used inline as `key=`
print(low.__name__, low.__doc__)
```

### Scope: LEGB
Name lookup goes **L**ocal → **E**nclosing function → **G**lobal (module) → **B**uilt-ins.
Python has **function scope, not block scope**: a variable assigned inside an `if` or `for` is still
visible after it (like `var`, unlike `let`).
```python
for i in range(3):
    last = i
print(i, last)    # 2 2: both still exist after the loop

if True:
    x = 10
print(x)          # 10
```
**Assignment makes a name local** to the whole function. That's why this fails:
```python
counter = 0
def bump():
    counter += 1     # UnboundLocalError: counter is local here because it's assigned
```
Fix it with `global counter` (avoid this in real code) or, better, don't use module-level mutable state.

### Closures and `nonlocal`
```python
def make_id_generator(start: int = 1):
    next_id = start

    def generate() -> int:
        nonlocal next_id          # rebind the ENCLOSING variable (like closure mutation in JS)
        current = next_id
        next_id += 1
        return current

    return generate

gen = make_id_generator(100)
gen(), gen()        # (100, 101)
```
Without `nonlocal`, `next_id += 1` would raise `UnboundLocalError`. Mutating a container
(`items.append`) doesn't need `nonlocal`, because that isn't rebinding the name.

**Late-binding gotcha** (the same idea as the old JS `var` in a loop bug):
```python
fns = [lambda: i for i in range(3)]
[f() for f in fns]                       # [2, 2, 2]
fns = [lambda i=i: i for i in range(3)]  # capture the current value as a default
[f() for f in fns]                       # [0, 1, 2]
```

### `functools` helpers
```python
from functools import partial, lru_cache

notify_ana = partial(assign, agent="ana")    # pre-fill arguments (like .bind)
notify_ana(42)

@lru_cache(maxsize=128)          # memoize; M0's get_settings() uses this!
def category_keywords(category: str) -> frozenset[str]:
    print("computing…")
    return frozenset({"refund", "invoice"}) if category == "billing" else frozenset()
```
`@lru_cache` is a **decorator** (chapter 08). For now, read it as "wrap this function".

### Docstrings & type hints
```python
def priority_score(urgency: int, impact: int, *, vip: bool = False) -> int:
    """Combine urgency (1-4) and impact (1-4) into a 1-20 score. VIPs get +4."""
    return urgency * impact + (4 if vip else 0)
```
Hints aren't enforced at runtime (just like TS types are erased), but editors, ruff and pyright use
them, and FastAPI/Pydantic **do** read them at runtime (chapter 09).

## Gotchas
- **Mutable defaults** (`=[]`, `={}`) are shared across calls. Use `None` + create inside.
- **Assignment inside a function makes the name local** everywhere in that function, which causes `UnboundLocalError`.
- **No block scope.** Loop variables leak out of the loop.
- **Lambdas are one expression only.** No statements, no multi-line bodies. Use `def` for anything bigger.
- **Calling with wrong args is a runtime `TypeError`.** Unlike JS, missing or extra arguments aren't silently `undefined` or ignored.
- **Closures capture variables, not values** (late binding).
- **`print(f)` vs `print(f())`.** Forgetting the parentheses passes the function object around silently.

## Exercises
Starter file: `exercises/ch03_functions.py`. Run `uv run python exercises/ch03_functions.py`.

1. `priority_score(urgency, impact, *, vip=False)` from above. Make `vip` keyword-only.
2. Fix `add_watcher(name, watchers=[])` so calls don't share state.
3. `make_counter()` returns a function that returns 1, 2, 3… on each call (`nonlocal`).
4. `build_query(**filters)` → `"category=billing&priority=3"`, skipping `None` values, keys sorted.
5. `apply_all(value, *funcs)` applies each function in order: `apply_all(" Hi ", str.strip, str.lower)` → `"hi"`.

<details><summary>Answers</summary>

```python
def priority_score(urgency: int, impact: int, *, vip: bool = False) -> int:
    return urgency * impact + (4 if vip else 0)

def add_watcher(name: str, watchers: list[str] | None = None) -> list[str]:
    watchers = [] if watchers is None else watchers
    watchers.append(name)
    return watchers

def make_counter():
    count = 0
    def counter() -> int:
        nonlocal count
        count += 1
        return count
    return counter

def build_query(**filters: object) -> str:
    return "&".join(f"{k}={v}" for k, v in sorted(filters.items()) if v is not None)

def apply_all(value, *funcs):
    for f in funcs:
        value = f(value)
    return value
```
`str.strip` is the *unbound method*. Calling `str.strip(" Hi ")` is the same as `" Hi ".strip()`.
</details>

## Apply to TriageDesk
No milestone, just practice. Look at `get_settings()` in `app/core/config.py`: it's a zero-argument
function wrapped by `@lru_cache`, so `Settings()` is built only once. Explain to yourself why that
matters when `.env` is read from disk. In M3, routes will receive dependencies as keyword
arguments (`session: AsyncSession = Depends(get_session)`). That's this chapter's default-argument syntax
used in a clever way.
