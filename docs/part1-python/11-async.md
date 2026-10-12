# 11 · Async Python vs the Node event loop

## Concept
You already understand the hard part: **a single thread, an event loop, and cooperative concurrency
for I/O**. Python's `asyncio` works on the same principle. When a coroutine `await`s something that
isn't ready (a network response, a DB query, a sleep), it hands control back to the event loop, which
runs another coroutine in the meantime.

The differences are what will trip you up:
1. **Python isn't async by default.** Node's whole runtime and standard library are non-blocking.
   Python's standard library (`time.sleep`, `open`, `requests`, `sqlite3`) is **blocking**. You opt
   into async by using async libraries (`httpx.AsyncClient`, `AsyncAnthropic`, SQLAlchemy's
   `AsyncSession`, `aiosqlite`).
2. **There's no implicit event loop.** Node starts one for you. In Python you start it explicitly
   with `asyncio.run(main())`, or a framework does it for you (FastAPI's server, uvicorn, runs the loop).
3. **Coroutines are lazy.** Calling an `async def` function returns a *coroutine object* and runs
   **nothing**. In JS, calling an async function starts running it immediately and returns a Promise.
4. **Python also has real threads and processes** for blocking or CPU-heavy work (`asyncio.to_thread`,
   thread pools, multiprocessing). FastAPI uses a thread pool for you (see below).

## In Node you'd…
| Node | Python asyncio |
|---|---|
| `async function f() {}` | `async def f(): ...` |
| `await p` | `await coro` |
| Calling `f()` starts it and returns a Promise | Calling `f()` returns a coroutine and **doesn't start it** |
| Event loop always running | `asyncio.run(main())` starts it (once, at the entrypoint) |
| `Promise.all([a(), b()])` | `await asyncio.gather(a(), b())` |
| `Promise.allSettled` | `gather(..., return_exceptions=True)` |
| `Promise.race` / timeout | `asyncio.wait_for(coro, timeout=5)` / `async with asyncio.timeout(5):` |
| Fire and forget: `doThing()` with no await | `task = asyncio.create_task(do_thing())` (and **keep a reference**!) |
| `setTimeout(r, ms)` promise | `await asyncio.sleep(seconds)` |
| p-limit (concurrency limit) | `asyncio.Semaphore(n)` |
| `for await (const x of stream)` | `async for x in stream:` |
| `async function*` | `async def` with `yield` (async generator) |
| `try/finally` around a connection | `async with client:` (async context manager) |
| `worker_threads` | `asyncio.to_thread(fn)`, thread pools |
| `fetch` / axios | `httpx.AsyncClient` (`requests` is sync only!) |

## Examples

### Hello asyncio
```python
import asyncio

async def fetch_ticket(ticket_id: int) -> dict:
    await asyncio.sleep(0.5)          # pretend this is a DB/HTTP call
    return {"id": ticket_id}

async def main() -> None:
    t = await fetch_ticket(1)
    print(t)

asyncio.run(main())                   # create the loop, run main to completion, close the loop
```
In the REPL you can use `uv run python -m asyncio`, which gives you top-level `await`.

### Coroutines are lazy (the #1 difference from JS)
```python
async def classify(text: str) -> str:
    print("classifying", text)
    return "billing"

coro = classify("refund")   # nothing printed! It's just a coroutine object
result = await coro         # NOW it runs (inside an async function)
```
If you forget `await`, you'll see `RuntimeWarning: coroutine 'classify' was never awaited`, and your
variable holds a coroutine instead of a string.

### Sequential vs concurrent: gather ≈ Promise.all
Classifying 3 tickets with an LLM, where each call takes ~1 second:
```python
import asyncio
import time

async def fake_llm(prompt: str) -> str:
    await asyncio.sleep(1)            # network latency
    return f"category for: {prompt}"

async def sequential(prompts: list[str]) -> list[str]:
    return [await fake_llm(p) for p in prompts]          # ~3s

async def concurrent(prompts: list[str]) -> list[str]:
    return await asyncio.gather(*(fake_llm(p) for p in prompts))   # ~1s, results in input order

async def main() -> None:
    prompts = ["refund", "login", "crash"]
    start = time.perf_counter()
    await concurrent(prompts)
    print(f"{time.perf_counter() - start:.1f}s")

asyncio.run(main())
```

### Error handling with gather
```python
results = await asyncio.gather(a(), b(), c())                         # first exception propagates
results = await asyncio.gather(a(), b(), c(), return_exceptions=True)  # like allSettled
for r in results:
    if isinstance(r, Exception):
        logger.warning("call failed: %r", r)
```

### TaskGroup: structured concurrency (3.11+, preferred for new code)
```python
async def triage_all(tickets: list[str]) -> list[str]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fake_llm(t)) for t in tickets]
    # leaving the block waits for every task. If one fails, the others are CANCELLED
    # and the errors are raised together as an ExceptionGroup.
    return [t.result() for t in tasks]
```
There's no direct JS equivalent. It's like `Promise.all` that also cancels the losers on failure.

### Limiting concurrency: Semaphore (≈ p-limit)
LLM APIs have rate limits, and firing 500 requests at once will get you 429s:
```python
sem = asyncio.Semaphore(5)                # at most 5 in flight

async def limited_llm(prompt: str) -> str:
    async with sem:
        return await fake_llm(prompt)

results = await asyncio.gather(*(limited_llm(p) for p in prompts))
```

### Timeouts
```python
try:
    async with asyncio.timeout(10):        # 3.11+
        reply = await fake_llm("draft a reply")
except TimeoutError:
    reply = None

reply = await asyncio.wait_for(fake_llm("x"), timeout=10)   # older equivalent
```

### create_task: background work (and the GC trap)
```python
async def main() -> None:
    task = asyncio.create_task(fake_llm("background"))   # starts running at the next await
    await do_other_stuff()
    result = await task                                   # collect it later
```
In JS an un-awaited promise keeps running. In Python, the loop holds only a **weak reference** to
tasks, so if you don't keep `task` somewhere, it can be garbage-collected mid-flight. Keep references
(or use a TaskGroup). For "after the response" work in FastAPI, use `BackgroundTasks` (chapter 18).

### The blocking-call trap ⚠️
```python
import time

async def bad() -> None:
    time.sleep(2)          # ❌ blocks the WHOLE event loop: every other request freezes
async def good() -> None:
    await asyncio.sleep(2) # ✅ yields control
```
Common blocking culprits inside `async def`:
- `time.sleep`, `requests.get`, the sync `anthropic.Anthropic()` client, `sqlite3`, heavy CPU work
  (e.g. computing embeddings locally, parsing a big PDF).

If you *must* call blocking code from async code, move it to a thread:
```python
def compute_embeddings(texts: list[str]) -> list[list[float]]:   # sync, CPU/IO heavy
    ...

vectors = await asyncio.to_thread(compute_embeddings, texts)     # runs in a worker thread
```
In Node, `fs.readFileSync` in a handler is the same sin. It's just much easier to commit in Python
because blocking is the default.

### async with / async for / async generators
```python
import httpx

async def get_status() -> int:
    async with httpx.AsyncClient(timeout=10) as client:   # async context manager: opens/closes the pool
        r = await client.get("https://example.com")
        return r.status_code

async def stream_tokens(prompt: str):                     # async generator
    for word in "Thanks for reaching out".split():
        await asyncio.sleep(0.1)
        yield word

async def main() -> None:
    async for token in stream_tokens("x"):                # like for await…of
        print(token, end=" ", flush=True)
```
LLM streaming (chapter 19) uses exactly this: `async for event in stream:`.

### Sync vs async endpoints in FastAPI
FastAPI accepts **both**, and treats them differently:
```python
@app.get("/a")
async def a():               # runs ON the event loop. Must never block!
    await asyncio.sleep(1)   # ✅
    return {"ok": True}

@app.get("/b")
def b():                     # plain def: FastAPI runs it in a THREAD POOL
    time.sleep(1)            # OK-ish: blocks only that worker thread
    return {"ok": True}
```
Rules of thumb:
- Use `async def` when everything inside is awaitable (an async DB session, `httpx.AsyncClient`, `AsyncAnthropic`). That's TriageDesk's default.
- Use plain `def` if you're calling blocking libraries and don't want to wrap them.
- **Never** call blocking code inside `async def`. That's the worst of both worlds.

Node doesn't have this choice because everything is async. In Python, picking the wrong one gives
you a server that handles exactly one request at a time.

### Why async matters for TriageDesk
A triage request waits on: DB insert (ms) → LLM classification (~1s) → vector search (ms) → LLM draft (~3s).
That's almost entirely **waiting on I/O**. With async, one process can serve hundreds of these
concurrently, exactly the Node.js value proposition.

## Gotchas
- **Forgetting `await`** gives you a coroutine object instead of a value, plus a "never awaited" warning.
- **`asyncio.run()` inside an already-running loop** (e.g. inside FastAPI or Jupyter) raises `RuntimeError`. Call `asyncio.run` once, at the very top only.
- **Blocking calls in `async def`** (`time.sleep`, `requests`, the sync SDK clients). Use async libraries or `asyncio.to_thread`.
- **`requests` is sync.** Use `httpx` (it has both sync and async APIs).
- **Async is contagious.** To `await` you have to be in an `async def`, so it spreads upward, same as JS.
- **Un-referenced `create_task`** can be garbage-collected. Keep the task or use a TaskGroup.
- **CPU-bound work doesn't benefit from asyncio.** The GIL means threads don't parallelise CPU-bound Python code either. Use processes (`ProcessPoolExecutor`) for real CPU parallelism.

## Exercises
Starter file: `exercises/ch11_async.py`. The solution is in `exercises/solutions/ch11_async.py`.
The asserts check timing too, so sequential solutions will fail.

1. `classify_all(texts)`: call `fake_llm` for each text **concurrently** and return the results in input order (gather).
2. `classify_limited(texts, limit)`: the same, but with at most `limit` calls in flight (Semaphore). The test checks max concurrency.
3. `classify_with_timeout(text, seconds)`: return the result, or `"timeout"` if it takes too long.
4. `safe_classify_all(texts)`: like 1, but a failing call (a text containing `"error"`) becomes `"failed"` instead of crashing everything.

<details><summary>Answers</summary>

```python
async def classify_all(texts):
    return list(await asyncio.gather(*(fake_llm(t) for t in texts)))

async def classify_limited(texts, limit):
    sem = asyncio.Semaphore(limit)
    async def one(t):
        async with sem:
            return await fake_llm(t)
    return list(await asyncio.gather(*(one(t) for t in texts)))

async def classify_with_timeout(text, seconds):
    try:
        async with asyncio.timeout(seconds):
            return await fake_llm(text)
    except TimeoutError:
        return "timeout"

async def safe_classify_all(texts):
    results = await asyncio.gather(*(fake_llm(t) for t in texts), return_exceptions=True)
    return ["failed" if isinstance(r, Exception) else r for r in results]
```
</details>

## Apply to TriageDesk: M2 async DB
- In M2 you'll install `sqlalchemy[asyncio]` + `aiosqlite` and use `AsyncSession`, so every DB call
  becomes `await session.execute(...)`. Your route handlers will be `async def`.
- The `get_session` dependency is an **async generator** wrapped around `async with` (chapters 07 + 11 combined).
- In M5/M6 you'll use the `AsyncAnthropic` client (not the sync `Anthropic` one) inside async routes,
  and `asyncio.to_thread` for any CPU-heavy local embedding work. That's the blocking-call trap avoided.
- `GET /health` in `app/api/routes/health.py` is currently a plain `def`. That's fine because it does
  no I/O. Explain to yourself why FastAPI would still run it in the thread pool.
