# 08 · Decorators

## Concept
A **decorator** is a function that takes a function and returns a (usually wrapped) function. The `@`
syntax is just shorthand:

```python
@timed
def classify(ticket): ...

# is exactly the same as:
def classify(ticket): ...
classify = timed(classify)
```

That works because functions in Python are ordinary objects. You can pass them around, store them,
and return them from other functions (chapter 03, closures). Decorators are how Python adds
cross-cutting behaviour such as logging, timing, retries, caching, auth checks and route registration
without touching the function body.

You'll use them constantly before you ever write one: `@app.get("/tickets")`, `@dataclass`,
`@property`, `@lru_cache`, `@contextmanager`, `@pytest.fixture`.

## In Node you'd…
| Node / TS | Python |
|---|---|
| Higher-order function: `const timed = fn => (...args) => {…}` | Same idea, plus `@timed` syntax sugar |
| Express middleware `app.use((req, res, next) => …)` | FastAPI middleware/dependencies (chapter 16). A decorator wraps *one* function, middleware wraps *every* request |
| `app.get("/x", handler)` | `@app.get("/x")` above `def handler()`: the decorator *registers* the function |
| TS/NestJS decorators `@Get()`, `@Injectable()` | Similar look, but Python decorators are plain runtime functions with no `experimentalDecorators` flag and no reflect-metadata |
| `lodash.memoize` | `functools.lru_cache` / `functools.cache` |
| `p-retry` | a `@retry` decorator (you'll write one below) |

## Examples

### Step 1: a basic wrapper
```python
import time

def timed(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)        # call the original
        print(f"{func.__name__} took {time.perf_counter() - start:.3f}s")
        return result
    return wrapper

@timed
def classify(text: str) -> str:
    time.sleep(0.1)
    return "billing" if "refund" in text else "general"

classify("refund please")   # prints "classify took 0.100s", returns 'billing'
```
`*args, **kwargs` lets the wrapper accept and forward *any* signature (chapter 03).

### Step 2: always use `functools.wraps`
Without it, the wrapped function loses its identity:
```python
classify.__name__   # 'wrapper'  ← bad: breaks logs, debugging, FastAPI, pytest
```
Fix:
```python
import functools

def timed(func):
    @functools.wraps(func)                    # copies __name__, __doc__, signature info…
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            print(f"{func.__name__} took {time.perf_counter() - start:.3f}s")
    return wrapper
```
FastAPI inspects function signatures to work out parameters, so a decorator *without* `wraps` on a
route handler will break it.

### Step 3: decorators with arguments (three levels deep)
`@retry(times=3)` means "call `retry(times=3)`, and the result is the real decorator":
```python
import functools
import random
import time

def retry(times: int = 3, delay: float = 0.5, exceptions: tuple[type[Exception], ...] = (Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == times:
                        raise                          # out of attempts: re-raise the last error
                    print(f"{func.__name__} failed ({e!r}), retry {attempt}/{times - 1}")
                    time.sleep(delay * 2 ** (attempt - 1))   # exponential backoff
        return wrapper
    return decorator

@retry(times=4, delay=0.1, exceptions=(ConnectionError,))
def call_llm(prompt: str) -> str:
    if random.random() < 0.5:
        raise ConnectionError("API overloaded")
    return "drafted reply"
```
This is a preview of chapter 19. LLM APIs fail transiently (rate limits, overloads), and retrying with
backoff is standard. (The Anthropic SDK has retries built in, but now you know how they work.)

### Stacking decorators
They're applied **bottom-up** (the one nearest the function wraps first) and run **top-down**:
```python
@timed            # outer: times the whole thing, including retries
@retry(times=3)   # inner: retries call_llm
def call_llm(prompt): ...

# same as: call_llm = timed(retry(times=3)(call_llm))
```

### Decorators that register (no wrapping)
This is how `@app.get(...)` works. It stores the function in a table and returns it unchanged:
```python
HANDLERS: dict[str, callable] = {}

def on(event: str):
    def decorator(func):
        HANDLERS[event] = func
        return func                  # no wrapper needed
    return decorator

@on("ticket.created")
def notify_agents(ticket): ...

HANDLERS["ticket.created"]({"id": 1})
```

### Class-based decorators (when you need state)
```python
class CountCalls:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.calls = 0

    def __call__(self, *args, **kwargs):     # makes instances callable like functions
        self.calls += 1
        return self.func(*args, **kwargs)

@CountCalls
def triage(ticket): ...

triage("x"); triage("y")
triage.calls   # 2
```
A closure with `nonlocal` can do the same thing (chapter 03). Choose whichever reads better.

### Built-in decorators you'll use
```python
from functools import lru_cache, cache

@lru_cache(maxsize=128)          # memoize; arguments must be hashable
def get_settings(): ...          # ← exactly what app/core/config.py does

class Ticket:
    @property                    # attribute-style getter (chapter 06)
    def is_urgent(self) -> bool: ...

    @staticmethod                # no self
    def normalize(text: str) -> str: ...

    @classmethod                 # receives the class, an alternative constructor
    def from_email(cls, raw: str) -> "Ticket": ...
```

### Decorating async functions
An `async def` returns a coroutine, so the wrapper must be `async` and `await` it:
```python
def timed_async(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            print(f"{func.__name__} took {time.perf_counter() - start:.3f}s")
    return wrapper
```
If you use a sync wrapper on an async function, it "finishes" instantly and only times creating the
coroutine, which is a classic bug.

### Typing decorators properly (advanced, revisit after chapter 09)
```python
from collections.abc import Callable

def timed[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(*args, **kwargs)
    return wrapper
```
`**P` (a ParamSpec) keeps the original signature, so your editor still autocompletes the arguments.

## Gotchas
- **Forgetting `@functools.wraps`** breaks `__name__`, docs, introspection and FastAPI.
- **`@retry` vs `@retry()`.** A decorator factory needs the parentheses. `@retry` without them passes the function as `times`, which fails in confusing ways.
- **Decorators run at import time.** `@app.get(...)` registers the route when the module is imported, and that's why `main.py` must import the routers.
- **Order matters when stacking.** `@timed @retry` measures all attempts, `@retry @timed` measures each attempt.
- **Sync wrapper on an async function** (see above).
- **`lru_cache` on methods** keeps `self` alive forever (a memory leak). Prefer module-level functions.

## Exercises
Starter file: `exercises/ch08_decorators.py`. The solution is in `exercises/solutions/ch08_decorators.py`.

1. `call_counter`: a decorator that adds a `.calls` attribute to the wrapped function and increments it on every call. Use `functools.wraps`.
2. `retry(times)`: retry on any exception, re-raise after `times` failed attempts (no sleeping, so tests stay fast).
3. `validate_priority`: a decorator for functions whose first argument is a priority string. Raise `ValueError` unless it's one of `low/medium/high/urgent`.
4. Confirm `functools.wraps` worked: `wrapped.__name__` should be the original name.

<details><summary>Answers</summary>

```python
import functools

def call_counter(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)
    wrapper.calls = 0
    return wrapper

def retry(times):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
        return wrapper
    return decorator

def validate_priority(func):
    @functools.wraps(func)
    def wrapper(priority, *args, **kwargs):
        if priority not in {"low", "medium", "high", "urgent"}:
            raise ValueError(f"invalid priority: {priority}")
        return func(priority, *args, **kwargs)
    return wrapper
```
</details>

## Apply to TriageDesk
- Look at `app/api/routes/health.py`: `@router.get("/health")` is a *registering* decorator. It stores
  `health` in the router's route table. Then look at `app/core/config.py`: `@lru_cache` makes
  `get_settings()` build `Settings` only once.
- In M6 you'll wrap LLM calls. Rather than hand-rolling `@retry`, you'll rely on the SDK's built-in
  retries, but you might add a `@timed_async`-style decorator (or plain logging) to record latency per call.
