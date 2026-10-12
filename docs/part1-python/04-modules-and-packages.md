# 04 · Modules & packages

## Concept
- A **module** is any `.py` file. Its top-level names (functions, classes, variables) are its public API.
- A **package** is a directory of modules, normally with an `__init__.py` file. Packages nest:
  `app/core/config.py` is the module `app.core.config`.
- `import` runs the module's top-level code **once**, caches the module object in `sys.modules`, and
  binds a name. Later imports reuse the cache (like Node's `require` cache).
- Python finds modules by searching the directories in **`sys.path`**. The first entry is the directory of
  the script you ran, or the current directory when you use `python -m`. This one fact explains most
  import errors.

## In Node you'd…
```js
// ESM
import { getSettings } from "./core/config.js";
import * as path from "node:path";
import express from "express";
export function health() {}
export default app;

// CommonJS
const { getSettings } = require("./core/config");
module.exports = { health };
```
```python
from app.core.config import get_settings     # absolute import (preferred)
from .config import get_settings             # relative import (inside a package)
import os.path                               # stdlib (like node:path)
import fastapi                               # third-party from .venv
from fastapi import FastAPI, APIRouter

def health(): ...                            # no export keyword: every top-level name is importable
```
| Node | Python |
|---|---|
| `export` / `module.exports` | nothing. All top-level names are public. `_leading_underscore` means "private by convention" |
| `export default` | doesn't exist. Always import by name |
| `index.js` in a folder | `__init__.py` in a folder |
| `import * as m from "m"` | `import m` (then `m.thing`) |
| `node_modules` resolution | `sys.path` (your project root + stdlib + `.venv/site-packages`) |
| `require.main === module` | `if __name__ == "__main__":` |
| `"type": "module"` vs CJS headaches | one system, no flavours |

## Examples

### Import styles
```python
import json                               # use as json.dumps(...)
import datetime as dt                     # alias: dt.datetime.now()
from pathlib import Path                  # bring in one name
from collections import Counter, defaultdict
from app.core.config import Settings, get_settings
# from os import *                        # avoid: pollutes your namespace, and linters complain
```
Style (enforced by ruff's `I` rules): imports go at the top, in three groups separated by blank lines:
**stdlib**, **third-party**, **your code**. Run `uv run ruff check --fix` to sort them.

### How `app.core.config` resolves in this repo
```
Python_Learning/          ← project root, on sys.path when you run from here
├── app/
│   ├── __init__.py       ← makes "app" a package
│   ├── main.py           ← app.main
│   ├── core/
│   │   ├── __init__.py   ← app.core
│   │   └── config.py     ← app.core.config
│   └── api/routes/health.py   ← app.api.routes.health
└── tests/test_health.py
```
- `uv run fastapi dev app/main.py`: the FastAPI CLI works out the package from the file path and puts the
  project root on `sys.path`, so `from app.core.config import …` works inside `app/main.py`.
- `uv run pytest`: `pyproject.toml` has `[tool.pytest.ini_options] pythonpath = ["."]`, which adds
  the root to `sys.path`, so tests can `from app.main import create_app`.
- `uv run python -m app.main`: `-m` means "run this module by its dotted name", and it puts the **current
  directory** on `sys.path`. This is the reliable way to run modules inside packages.
- `uv run python app/main.py`: puts **`app/`** (the script's folder) on `sys.path`, not the root. Then
  `import app...` fails with `ModuleNotFoundError: No module named 'app'`. That's the classic beginner trap.

Debug any import issue with:
```python
import sys; print(sys.path)
import app.core.config as c; print(c.__file__)
```

### Absolute vs relative imports
```python
# inside app/api/routes/health.py
from app.core.config import get_settings     # absolute: always works, easy to grep (we use this)
from ...core.config import get_settings      # relative: . = this package, .. = parent, ... = grandparent
```
Relative imports only work inside a package that was imported as a package (not a script run directly).
This project's convention is **absolute imports from `app.`**.

### `__init__.py`
- It runs when the package is first imported. It's usually empty (as in this repo).
- You can use it to **re-export** a clean API (like `index.js` barrel files):
```python
# app/schemas/__init__.py  (example for later)
from app.schemas.ticket import TicketCreate, TicketRead

__all__ = ["TicketCreate", "TicketRead"]    # what `from app.schemas import *` exports
```
- Without `__init__.py` a directory becomes an implicit "namespace package". It still imports, but stick to
  real packages in app code because tooling handles them more predictably.

### `if __name__ == "__main__":`
Every module has a `__name__`. It's `"__main__"` when the file is run directly, and its dotted name
(`"app.core.config"`) when imported.
```python
# scripts/seed_kb.py (later milestone)
def main() -> None:
    ...

if __name__ == "__main__":     # run only when executed, not when imported (e.g. by tests)
    main()
```
All the exercise files use this pattern.

### Import-time side effects
Top-level code runs on import, so keep modules cheap to import:
```python
# BAD: opens a DB connection just because someone imported the module
conn = connect(DATABASE_URL)

# GOOD: do it inside a function / on startup
def get_connection(): ...
```
`app/main.py` does `app = create_app()` at module level on purpose, because the server needs a
module-level `app` object. Everything else stays inside functions.

### Circular imports
`a` imports `b`, and `b` imports `a` → `ImportError: cannot import name … (most likely due to a circular
import)`. Fixes, in order of preference: move the shared code into a third module, import inside the
function that needs it, or use `from __future__ import annotations` / `TYPE_CHECKING` for imports that
are only needed for type hints (chapter 09). Layering (routes → services → models) prevents most cycles.

### Standard library vs third-party
The stdlib is large ("batteries included"): `json`, `pathlib`, `datetime`, `logging`, `asyncio`,
`re`, `uuid`, `secrets`, `hashlib`, `csv`, `sqlite3`, `dataclasses`, `typing`, `unittest`… Before
`uv add` for something small, check whether the stdlib already does it.

## Gotchas
- **`python app/main.py` ≠ `python -m app.main`.** The first breaks package imports.
- **Naming a file after a stdlib or third-party module** (`json.py`, `fastapi.py`, `test.py`, `random.py`) shadows the real one.
  Your `import json` silently imports your own file. Rename it and delete its `__pycache__`.
- **There's no `export default`.** Import names explicitly.
- **Modules are singletons.** Module-level variables are shared process-wide (useful for caches,
  dangerous for per-request state).
- **Changes need a restart** in a plain REPL. `importlib.reload(mod)` exists, but it's fiddly. The dev server reloads for you.
- **`__pycache__/` folders** hold compiled bytecode. They're gitignored and safe to delete.

## Exercises
This one is a small package: `exercises/ch04_modules/`.
```
exercises/ch04_modules/
├── __init__.py
├── main.py          ← the checks; run it as a MODULE
└── triage/
    ├── __init__.py  ← TODO: re-export classify
    ├── text.py      ← normalize() (done)
    └── rules.py     ← TODO: import normalize (relative import) + implement classify()
```
Run from the project root:
```bash
uv run python -m exercises.ch04_modules.main
```
1. Implement `classify(text)` in `triage/rules.py` using a **relative import** of `normalize`.
2. Re-export `classify` from `triage/__init__.py` and set `__all__`.
3. Now try `uv run python exercises/ch04_modules/main.py`. Read the error and explain it.
4. In the REPL: `import exercises.ch04_modules.triage.rules as r; r.__name__, r.__file__`.

Solution package: `exercises/solutions/ch04_modules/` (run with `uv run python -m exercises.solutions.ch04_modules.main`).

<details><summary>Answers</summary>

```python
# triage/rules.py
from .text import normalize

KEYWORDS = {"billing": {"refund", "invoice", "charge", "charged"}, "auth": {"login", "password", "2fa"}}

def classify(text: str) -> str:
    words = set(normalize(text).split())
    for category, keywords in KEYWORDS.items():
        if words & keywords:
            return category
    return "other"

# triage/__init__.py
from .rules import classify

__all__ = ["classify"]
```
3. When you run the file directly, `sys.path[0]` is `exercises/ch04_modules/` and the module's
`__name__` is `"__main__"` with no parent package, so `from .triage import …` fails with
`ImportError: attempted relative import with no known parent package`. `-m` runs it *as part of the package*.
</details>

## Apply to TriageDesk: M0 review
Re-read the M0 imports with this chapter in mind:
1. `app/main.py` imports `from app.api.routes import health`. Which file is that, and why does
   `app/api/routes/__init__.py` need to exist?
2. Why is `app = create_app()` at module level in `main.py`, while `Settings()` is only built inside
   `get_settings()`?
3. Run `uv run python -c "import app.main; print(app.main.app.title)"` from the root, then from inside
   `app/`. Explain the difference.
4. The imports in `app/main.py` are grouped third-party (`fastapi`) → local (`app.…`). Swap the order on purpose and run
   `uv run ruff check .`.
