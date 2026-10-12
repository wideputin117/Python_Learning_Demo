# 12 · Testing with pytest

## Concept
**pytest** is the de-facto Python test runner. It's more minimal than Jest:
- A test is **any function named `test_*`** in a file named `test_*.py`. There's no `describe`/`it` and no imports needed.
- Assertions are the plain **`assert`** statement. pytest rewrites it to show rich diffs on failure, so there's no `expect().toBe()` chain.
- Setup and teardown are done with **fixtures**: functions that pytest *injects* by matching parameter
  names (dependency injection, the same idea FastAPI uses).

The project config lives in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]      # where `uv run pytest` looks by default
pythonpath = ["."]         # so tests can `import app...`
```

## In Node you'd…
| Jest / Vitest | pytest |
|---|---|
| `describe("x", () => { it("y", …) })` | `def test_y():` (optionally group tests in a `class TestX:`) |
| `expect(a).toBe(b)` / `toEqual` | `assert a == b` |
| `expect(x).toBeTruthy()` | `assert x` |
| `expect(() => f()).toThrow(Err)` | `with pytest.raises(Err, match="msg"): f()` |
| `expect(n).toBeCloseTo(0.3)` | `assert n == pytest.approx(0.3)` |
| `beforeEach` / `afterEach` | a **fixture** (`yield` splits setup from teardown) |
| `beforeAll` | a fixture with `scope="module"` or `"session"` |
| `test.each([...])` | `@pytest.mark.parametrize("a,b", [...])` |
| `jest.mock("module")` | `monkeypatch.setattr(...)` or `unittest.mock.patch(...)` |
| `jest.fn()` | `unittest.mock.Mock()` / `MagicMock()` / `AsyncMock()` |
| `fn.mockReturnValue(x)` / `mockRejectedValue(e)` | `m.return_value = x` / `m.side_effect = e` |
| `expect(fn).toHaveBeenCalledWith(a)` | `m.assert_called_once_with(a)` |
| `process.env.X = "1"` in a test | `monkeypatch.setenv("X", "1")` (auto-restored) |
| `test.skip` / `test.only` | `@pytest.mark.skip` / `pytest -k name` |
| `--watch` | `uv add --dev pytest-watcher` → `uv run ptw` |
| `--coverage` | `uv add --dev pytest-cov` → `uv run pytest --cov=app` |
| supertest | FastAPI `TestClient` (in-process, no real server) |

## Examples

### The basics
```python
# tests/test_priority.py
import pytest

def guess_priority(text: str) -> str:
    text = text.lower()
    if "down" in text or "outage" in text:
        return "urgent"
    if "refund" in text or "charged" in text:
        return "high"
    return "low"

def test_outage_is_urgent():
    assert guess_priority("Site is DOWN") == "urgent"

def test_default_is_low():
    assert guess_priority("How do I change my avatar?") == "low"
```
Running tests:
```bash
uv run pytest                     # everything under tests/
uv run pytest tests/test_priority.py
uv run pytest -k urgent           # tests whose name matches "urgent"
uv run pytest -x                  # stop at the first failure
uv run pytest --lf                # rerun only the last failures
uv run pytest -v                  # verbose: one line per test
uv run pytest -s                  # don't capture output (see your print()s)
```

### When an assert fails, pytest shows you why
```python
def test_tags():
    assert sorted(["billing", "refund"]) == ["billing", "refunds"]
# E  AssertionError: assert ['billing', 'refund'] == ['billing', 'refunds']
# E    At index 1 diff: 'refund' != 'refunds'
```

### Parametrize ≈ test.each
```python
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Checkout is down", "urgent"),
        ("I was charged twice", "high"),
        ("Please refund me", "high"),
        ("Dark mode?", "low"),
    ],
)
def test_guess_priority(text: str, expected: str):
    assert guess_priority(text) == expected
```
Each tuple becomes its own test case with its own pass/fail line. Use `ids=[...]` for readable names.

### Exceptions and floats
```python
def test_invalid_priority_rejected():
    with pytest.raises(ValueError, match="invalid priority"):
        set_priority("asap")

def test_similarity():
    assert cosine([1, 0], [1, 1]) == pytest.approx(0.7071, abs=1e-4)
```

### Fixtures: setup/teardown by injection
```python
import pytest

@pytest.fixture
def sample_tickets() -> list[dict]:
    return [
        {"id": 1, "title": "Login broken", "priority": "high"},
        {"id": 2, "title": "Dark mode?", "priority": "low"},
    ]

def test_count(sample_tickets):          # pytest sees the parameter name and calls the fixture
    assert len(sample_tickets) == 2
```
Every test gets a **fresh** fixture value (the default `scope="function"`, like `beforeEach`).

**Teardown with `yield`** is the same pattern as `@contextmanager` (chapter 07):
```python
@pytest.fixture
def db():
    conn = connect(":memory:")   # setup
    yield conn                   # the test runs here
    conn.close()                 # teardown, runs even if the test failed
```

**Fixtures can use other fixtures:**
```python
@pytest.fixture
def queue(sample_tickets):
    q = TicketQueue()
    for t in sample_tickets:
        q.add(t)
    return q
```

**Scopes:** `@pytest.fixture(scope="session")` runs once for the whole test run (e.g. creating a test DB engine).

### conftest.py: shared fixtures
Put fixtures in `tests/conftest.py`, and every test file in that directory can use them **without importing**.
TriageDesk will grow one like this:
```python
# tests/conftest.py (M3 onwards)
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())
```

### Built-in fixtures worth knowing
```python
def test_writes_report(tmp_path):             # a fresh temp directory (pathlib.Path)
    out = tmp_path / "report.json"
    write_report(out)
    assert out.exists()

def test_prints(capsys):                      # capture stdout/stderr
    print("hello")
    assert capsys.readouterr().out == "hello\n"

def test_logs_warning(caplog):                # capture logging
    with caplog.at_level("WARNING"):
        check_sla(ticket)
    assert "SLA" in caplog.text

def test_env(monkeypatch):                    # patch env/attributes, auto-undone after the test
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
```

### Mocking: monkeypatch vs unittest.mock
**monkeypatch** replaces an attribute for the duration of one test. It's simple and explicit:
```python
import app.ai.triage as triage_module

def test_triage_uses_fallback(monkeypatch):
    def fake_classify(text: str) -> str:
        raise ConnectionError("API down")
    monkeypatch.setattr(triage_module, "call_llm", fake_classify)
    assert triage_module.triage("refund") == "general"
```
**`unittest.mock`** gives you Jest-style spies with call assertions:
```python
from unittest.mock import Mock, AsyncMock, patch

llm = Mock()
llm.classify.return_value = "billing"
assert triage("refund pls", llm=llm) == "billing"
llm.classify.assert_called_once_with("refund pls")

llm.classify.side_effect = TimeoutError("slow")     # make it raise
llm.classify.side_effect = ["a", "b"]               # successive return values

async_llm = AsyncMock()                             # for async methods: awaiting returns return_value
async_llm.complete.return_value = "draft"

with patch("app.ai.triage.call_llm", return_value="billing") as m:   # patch where it's LOOKED UP
    ...
```
**Patch where it's used, not where it's defined.** If `app/ai/triage.py` does
`from app.ai.llm import call_llm`, patch `"app.ai.triage.call_llm"`, not `"app.ai.llm.call_llm"`.
This is the most common mocking bug in Python.

**Prefer dependency injection to patching.** If `triage(text, llm)` takes the client as a parameter
(or as a FastAPI dependency), tests just pass a fake. There's no patching at all. That's why
CLAUDE.md says AI calls are wrapped in `app/ai/llm.py` and injected.

### Testing FastAPI: TestClient ≈ supertest
```python
from fastapi.testclient import TestClient
from app.main import create_app

def test_health():
    client = TestClient(create_app())
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```
This runs the app in-process with no port and no server. From M3 on you'll override dependencies:
`app.dependency_overrides[get_llm] = lambda: FakeLLM()`, which is FastAPI's built-in, cleaner version of `jest.mock`.

### Async tests
`anyio` is already installed (FastAPI depends on it), and it ships a pytest plugin:
```python
import pytest

@pytest.mark.anyio
async def test_async_thing():
    assert await fetch_ticket(1) == {"id": 1}

@pytest.fixture
def anyio_backend():          # put this in conftest.py: run on asyncio only
    return "asyncio"
```
(The alternative is `pytest-asyncio` with `@pytest.mark.asyncio`. Pick one per project.)

### Test layout (Arrange, Act, Assert)
```python
def test_high_priority_tickets_come_first(queue):
    # arrange: done by the fixture
    # act
    first = queue.next()
    # assert
    assert first["priority"] == "high"
```
One behaviour per test, and a name that describes the behaviour: `test_<unit>_<does what>_<when>`.

## Gotchas
- **File and function names matter.** Only `test_*.py` files and `test_*` functions are collected. `tests_foo.py` or `check_x()` are silently ignored.
- **Patching the wrong path** (see above). Patch where the name is looked up.
- **Mutable module-level state leaks between tests** (e.g. an in-memory ticket store). Reset it in a fixture, or build fresh objects per test (that's why M0 uses `create_app()`, a factory).
- **Tests calling real external services.** Project rule: tests **never** call the real Claude API. Inject fakes.
- **`assert` with parentheses and a comma**: `assert (x == 1, "msg")` asserts a non-empty tuple, so it's *always true*. Write `assert x == 1, "msg"`.
- **Duplicate test file basenames** in different folders, without `__init__.py`, cause "import file mismatch". Use unique names or packages.
- **`Mock()` accepts any attribute**, so typos pass silently. Use `Mock(spec=RealClass)` or `create_autospec` to catch them.

## Exercises
Folder: `exercises/ch12_testing/`
- `triage_rules.py` is a small, complete module (the code under test). Read it first.
- `test_triage_rules.py` has test stubs that currently `pytest.fail("TODO")`. Write each test.

Run: `uv run pytest exercises/ch12_testing -v`. The solution is in
`exercises/solutions/ch12_testing/test_triage_rules_solution.py` (run it with `uv run pytest exercises/solutions/ch12_testing -v`).

1. Parametrize `guess_priority` over at least 5 inputs, including case-insensitivity.
2. Write a `queue` fixture with 3 tickets, then test that `TicketQueue.next()` returns them in priority order.
3. Test that adding a ticket with an invalid priority raises `ValueError` with a helpful message.
4. Using `Mock`, test that `triage()` returns the LLM's category and calls it exactly once with the text. Test that it falls back to `"general"` when the LLM raises.
5. Using `monkeypatch.setenv`, test `confidence_threshold()` with and without the `TRIAGE_CONFIDENCE` env var.

<details><summary>Answers (sketch)</summary>

```python
@pytest.mark.parametrize(("text", "expected"), [
    ("Site is DOWN", "urgent"), ("charged twice", "high"),
    ("refund", "high"), ("dark mode?", "low"), ("Outage in EU", "urgent"),
])
def test_guess_priority(text, expected):
    assert guess_priority(text) == expected

@pytest.fixture
def queue():
    q = TicketQueue()
    q.add({"id": 1, "priority": "low"})
    q.add({"id": 2, "priority": "urgent"})
    q.add({"id": 3, "priority": "high"})
    return q

def test_queue_order(queue):
    assert [queue.next()["id"] for _ in range(3)] == [2, 3, 1]

def test_triage_falls_back(monkeypatch):
    llm = Mock()
    llm.classify.side_effect = ConnectionError
    assert triage("x", llm) == "general"
```
See the solution file for all of them.
</details>

## Apply to TriageDesk: M3 testing
1. Read `tests/test_health.py`. It already follows Arrange/Act/Assert and uses `create_app()` so each test gets a fresh app.
2. In M3 you'll add `tests/conftest.py` with a `client` fixture, test every endpoint (happy path + validation errors + 404s), and use `app.dependency_overrides` for the DB session and the LLM.
3. From M6 on, every AI feature gets a test with a **fake LLM** (a Protocol implementation or an `AsyncMock`), never the real API. M8 adds a separate *eval script* for checking real model quality. That's a different thing from unit tests (chapter 23).
