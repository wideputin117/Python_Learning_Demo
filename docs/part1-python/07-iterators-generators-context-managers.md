# 07 · Iterators, generators, context managers

## Concept
Two protocols show up everywhere in Python, including FastAPI, SQLAlchemy and the AI code later in this course:

1. **The iteration protocol.** Anything you can `for x in …` over is an *iterable*. Calling `iter(obj)`
   gives you an *iterator*, and calling `next(iterator)` on it gives the next value until it raises
   `StopIteration`. Lists, dicts, strings, files, `range` and DB result sets all follow this protocol.
2. **The context manager protocol.** Anything usable with `with … as x:` sets something up, hands
   you a value and **always** cleans up, even when an exception is raised. Files, locks, DB sessions,
   HTTP clients and temp directories all work this way.

**Generators** are the easy way to build iterators. A function that contains `yield` returns a lazy
generator object instead of running straight away. Each `next()` call runs the function until the next `yield`.

## In Node you'd…
| Node / JS | Python |
|---|---|
| `[Symbol.iterator]()` + `next()` returning `{value, done}` | `__iter__()` + `__next__()`, raises `StopIteration` when done |
| `function* gen() { yield 1 }` | `def gen(): yield 1` (no special syntax, `yield` alone makes it a generator) |
| `yield* other()` | `yield from other()` |
| `async function*` + `for await` | `async def` + `yield` → `async for` (chapter 11) |
| Readable streams for big data | Generators: lazy, constant memory |
| `try { … } finally { conn.release() }` | `with get_conn() as conn: …` |
| TC39 `using x = …` (explicit resource management) | `with` has existed for ~20 years |

The biggest mindset shift is that Python devs use generators **all the time**, while most JS devs rarely
write `function*`. Lazy pipelines are idiomatic Python.

## Examples

### Iterables vs iterators
```python
tickets = ["login broken", "refund please", "app crashes"]
it = iter(tickets)        # list is iterable → get an iterator
next(it)                  # 'login broken'
next(it)                  # 'refund please'
next(it)                  # 'app crashes'
next(it)                  # raises StopIteration
next(iter([]), "empty")   # default instead of raising: 'empty'
```
A `for` loop is exactly `iter()` followed by repeated `next()` until `StopIteration`.

**An iterator is consumed once:**
```python
it = iter([1, 2, 3])
list(it)   # [1, 2, 3]
list(it)   # []  ← already exhausted
```

### A custom iterator class (rarely needed, but useful to understand)
```python
class Countdown:
    def __init__(self, start: int) -> None:
        self.current = start

    def __iter__(self) -> "Countdown":
        return self

    def __next__(self) -> int:
        if self.current <= 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1

list(Countdown(3))  # [3, 2, 1]
```

### The same thing as a generator (what you'd actually write)
```python
def countdown(start: int):
    while start > 0:
        yield start
        start -= 1

gen = countdown(3)   # nothing has run yet!
next(gen)            # 3: runs until the first yield, then pauses
list(gen)            # [2, 1]: resumes from where it paused
```

### Generator for KB chunking (a preview of RAG, chapter 22)
Splitting a big document into overlapping chunks *lazily* means you never hold all the chunks in memory:
```python
from collections.abc import Iterator

def chunk_text(text: str, size: int = 500, overlap: int = 50) -> Iterator[str]:
    """Yield overlapping character windows of `text`."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    step = size - overlap
    for start in range(0, len(text), step):
        chunk = text[start : start + size]
        if chunk.strip():
            yield chunk
        if start + size >= len(text):
            break

for i, chunk in enumerate(chunk_text(open("faq.md").read(), size=200)):
    print(i, chunk[:40])
```

### Generator expressions
Like a list comprehension but with `()`. They're lazy, so you never build a full list:
```python
total_chars = sum(len(t) for t in tickets)          # no intermediate list
urgent = (t for t in tickets if "crash" in t)       # nothing computed yet
any("refund" in t for t in tickets)                 # short-circuits at the first match
```
Rule of thumb: if you're only going to loop over it once (`sum`, `any`, `max`, `"".join`), use a generator expression.

### Pipelines (like piping streams)
```python
def read_lines(path: str) -> Iterator[str]:
    with open(path, encoding="utf-8") as f:
        for line in f:            # files are lazy iterators of lines
            yield line.rstrip("\n")

def non_empty(lines: Iterator[str]) -> Iterator[str]:
    return (line for line in lines if line.strip())

def numbered(lines: Iterator[str]) -> Iterator[tuple[int, str]]:
    yield from enumerate(lines, start=1)

for n, line in numbered(non_empty(read_lines("faq.md"))):
    ...
```
Each stage pulls one item at a time from the previous one, so memory stays constant even for a 5 GB file.

### `yield from`
```python
def all_chunks(docs: list[str]) -> Iterator[str]:
    for doc in docs:
        yield from chunk_text(doc)   # delegate to another generator
```

### Context managers: `with`
```python
with open("faq.md", encoding="utf-8") as f:
    text = f.read()
# f is closed here, even if read() raised
```
`with` is equivalent to this:
```python
f = open("faq.md")
try:
    text = f.read()
finally:
    f.close()
```
You can open several at once: `with open(a) as src, open(b, "w") as dst: …`

### Writing a context manager: the class way
```python
import time

class Timer:
    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self                       # this is what `as t` receives

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.elapsed = time.perf_counter() - self.start
        print(f"took {self.elapsed:.3f}s")
        return False                      # False = don't swallow exceptions

with Timer() as t:
    sum(range(1_000_000))
```
`__exit__` receives the exception (if one happened). Returning `True` suppresses it, which is rarely what you want.

### Writing a context manager: the generator way (`@contextmanager`)
This is how most people write them. The code before `yield` is setup, the yielded value is the `as`
target, and the code after `yield` is cleanup:
```python
from collections.abc import Iterator
from contextlib import contextmanager

@contextmanager
def fake_db_session() -> Iterator[dict]:
    session = {"open": True, "pending": []}
    print("BEGIN")
    try:
        yield session
        print("COMMIT")          # only runs if the body didn't raise
    except Exception:
        print("ROLLBACK")
        raise                    # re-raise so the caller still sees the error
    finally:
        session["open"] = False
        print("CLOSE")

with fake_db_session() as s:
    s["pending"].append("insert ticket")
# BEGIN, COMMIT, CLOSE
```
Keep this pattern in mind. It's **exactly** how FastAPI's `yield` dependencies work (chapter 16) and
how the DB session in M2 is managed.

### Useful helpers in `contextlib`
```python
from contextlib import suppress, ExitStack

with suppress(FileNotFoundError):     # like try/except: pass, but explicit
    os.remove("tmp.txt")

with ExitStack() as stack:            # a dynamic number of context managers
    files = [stack.enter_context(open(p)) for p in paths]
```

### `itertools` teaser (more in chapter 10)
```python
from itertools import islice, batched   # batched is new in 3.12

list(islice(countdown(100), 3))         # [100, 99, 98]: take the first 3 of a lazy stream
list(batched(range(7), 3))              # [(0, 1, 2), (3, 4, 5), (6,)]: batch for embedding API calls
```

## Gotchas
- **Generators are single-use.** If you pass a generator to two functions, the second one sees nothing. Convert it with `list(gen)` if you need it twice.
- **Calling a generator function doesn't run it.** `chunk_text(text)` just creates the generator. Errors inside (like that `ValueError`) only appear when you start iterating. If you need eager validation, check arguments in a normal wrapper function that then returns the generator.
- **Don't modify a list while iterating over it.** Iterate over a copy (`for x in lst[:]`) or build a new list.
- **`return` inside a generator** stops iteration. It doesn't hand the value to the `for` loop.
- **Forgetting `try/finally` in a `@contextmanager`** means cleanup won't run if the body raises.
- **Variables assigned inside `with` still exist after it.** `with` doesn't create a scope (Python has function scope, not block scope).

## Exercises
Starter file: `exercises/ch07_generators.py`. Run it with `uv run python exercises/ch07_generators.py`
and make the asserts pass. The solution is in `exercises/solutions/ch07_generators.py`.

1. `fibonacci()`: an infinite generator of Fibonacci numbers. Use `islice` to take the first 10.
2. `chunk_words(text, size)`: yield lists of `size` words (the last one can be shorter).
3. `read_tickets(lines)`: a pipeline that strips whitespace, skips blank lines and `#` comments, and yields lowercased text.
4. `timer()`: a `@contextmanager` that yields a dict and stores `elapsed` (seconds) in it on exit, even if the body raises.

<details><summary>Answers</summary>

```python
from contextlib import contextmanager
from itertools import islice
import time

def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

list(islice(fibonacci(), 10))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

def chunk_words(text, size):
    words = text.split()
    for i in range(0, len(words), size):
        yield words[i : i + size]

def read_tickets(lines):
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            yield line.lower()

@contextmanager
def timer():
    result = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed"] = time.perf_counter() - start
```
</details>

## Apply to TriageDesk: M2 preview
In M2 you'll write this (don't write it yet, just recognise the shape):
```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:   # an async context manager
        yield session                        # FastAPI injects this into the route
    # cleanup runs after the response is sent
```
That's a generator **plus** a context manager, the two ideas from this chapter combined. FastAPI calls
`next()` to get the session, runs your route, then resumes the generator so the cleanup runs. The KB
`chunk_text` generator above will also come back in M5.
