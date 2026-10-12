# 00 · Setup: uv, virtual environments, editor

## Concept
Python needs three things before you write code:
1. **An interpreter**. You have Python 3.12 (`python3 --version`).
2. **An isolated environment per project** (a *virtual environment*, `.venv/`). This is where the
   project's packages are installed, so they don't pollute the system Python.
3. **A package/project manager** to install dependencies and pin versions. We use **uv**, a very
   fast modern tool that replaces pip + venv + pip-tools + pyenv.

## In Node you'd…
| Node | Python (uv) |
|---|---|
| `package.json` | `pyproject.toml` |
| `package-lock.json` | `uv.lock` |
| `node_modules/` (per project) | `.venv/` (per project) |
| `npm install` | `uv sync` |
| `npm install express` | `uv add fastapi` |
| `npm install -D jest` | `uv add --dev pytest` |
| `npx some-tool` / `npm run x` | `uv run some-tool` |
| `node script.js` | `uv run python script.py` |
| `nvm use 20` | `.python-version` file (uv reads it) |
| npmjs.com | pypi.org |
| `nodemon` | `fastapi dev` (auto-reload) |
| eslint + prettier | `ruff check` + `ruff format` |
| jest | pytest |

One important difference: Node resolves `node_modules` automatically by walking up directories. Python
uses whichever interpreter you run. If you run plain `python` you get the *system* Python, which
doesn't have your packages. `uv run …` always uses the project's `.venv`. You can also activate it:
`source .venv/bin/activate` (then `python`, `pytest` etc. refer to the venv, and `deactivate` exits).

## Examples
```bash
# uv is installed at ~/.local/bin/uv. Make sure it's on PATH (add to ~/.bashrc once):
source ~/.local/bin/env

uv --version
uv sync                      # create .venv and install everything from uv.lock
uv run python                # REPL inside the venv. Try: import fastapi; fastapi.__version__
uv run pytest                # run tests
uv run fastapi dev app/main.py   # open http://localhost:8000/docs
uv add httpx                 # add a runtime dependency (updates pyproject.toml + uv.lock)
uv remove httpx              # and remove it
uv tree                      # dependency tree (like npm ls)
```

**The REPL is your best friend.** Python's interactive shell is much more useful than Node's for
exploring. Use `help(obj)`, `dir(obj)` (lists attributes) and `type(obj)`:
```python
>>> s = "hello"
>>> type(s)
<class 'str'>
>>> [m for m in dir(s) if not m.startswith("_")][:5]
['capitalize', 'casefold', 'center', 'count', 'encode']
>>> help(s.split)
```

### Editor setup (VS Code)
- Install the extensions **Python** (Microsoft), **Pylance** (types/IntelliSense) and **Ruff** (lint + format).
- `Ctrl+Shift+P → Python: Select Interpreter → ./.venv/bin/python`. Without this, imports show red squiggles.
- Optional `settings.json`: `"[python]": {"editor.defaultFormatter": "charliermarsh.ruff", "editor.formatOnSave": true}`.

## Node → Python cheat sheet
| JavaScript | Python |
|---|---|
| `const x = 1; let y = 2` | `x = 1` (no keyword; constants are `UPPER_CASE` by convention) |
| `null` / `undefined` | `None` (only one!) |
| `true` / `false` | `True` / `False` |
| `&&` `\|\|` `!` | `and` `or` `not` |
| `===` | `==` (no type coercion in Python, so there's no `===`) |
| `` `Hi ${name}` `` | `f"Hi {name}"` |
| `// comment` / `/* */` | `# comment` / `"""docstring"""` |
| `{ }` blocks | indentation (4 spaces) + `:` |
| `if (a) {} else if (b) {}` | `if a: … elif b: … else: …` |
| `arr.length` | `len(arr)` |
| `arr.push(x)` | `lst.append(x)` |
| `arr.map(x => x*2)` | `[x * 2 for x in lst]` |
| `arr.filter(x => x>1)` | `[x for x in lst if x > 1]` |
| `for (const x of arr)` | `for x in lst:` |
| `for (let i=0;i<n;i++)` | `for i in range(n):` |
| `arr.forEach((x, i) => …)` | `for i, x in enumerate(lst):` |
| `Object.entries(o)` | `d.items()` |
| `o.key ?? "default"` | `d.get("key", "default")` |
| `const {a, b} = obj` | `a, b = d["a"], d["b"]` |
| `[...a, ...b]` / `{...o1, ...o2}` | `[*a, *b]` / `{**d1, **d2}` (or `d1 \| d2`) |
| `function f(a, b = 2) {}` | `def f(a, b=2):` |
| `(...args) => {}` | `def f(*args, **kwargs):` |
| `class A extends B { constructor() {} }` | `class A(B): def __init__(self): …` |
| `this` | `self` (explicit first parameter) |
| `try {} catch (e) {} finally {}` | `try: … except Exc as e: … finally: …` |
| `throw new Error("x")` | `raise ValueError("x")` |
| `import x from "y"` | `from y import x` |
| `module.exports` / `export` | everything top-level is importable; `_name` means "private" by convention |
| `async/await`, `Promise.all` | `async/await`, `asyncio.gather` |
| `JSON.parse` / `JSON.stringify` | `json.loads` / `json.dumps` |
| `console.log` | `print` (and `logging` for real apps) |
| `typeof x` | `type(x)`, `isinstance(x, int)` |

## Gotchas
- **Indentation is syntax.** Mixing tabs and spaces breaks code. Use 4 spaces (your editor + ruff handle it).
- **`python` vs `python3`.** On Linux the system command is `python3`. Inside an activated venv or with `uv run`, `python` works.
- **Don't `pip install` globally.** On Ubuntu it's blocked anyway ("externally-managed-environment"). Always `uv add`.
- **Commit `uv.lock`, never `.venv/`** (same as committing the lockfile but not `node_modules`).

## Exercises
1. Run `uv sync`, then `uv run python -c "import sys; print(sys.executable)"`. Confirm the path is inside `.venv`.
2. Run `python3 -c "import fastapi"` (system Python). Why does it fail when `uv run python -c "import fastapi"` works?
3. Start the dev server, open `/docs`, and call `GET /health` from the Swagger UI.
4. Run `uv tree` and find which package brings in `starlette`.

<details><summary>Answers</summary>

2. System Python doesn't have the project's packages. They live only in `.venv/`.
4. `fastapi` depends on `starlette`. FastAPI is built on top of Starlette (a bit like Express being built on Node's `http`).
</details>

## Apply to TriageDesk: M0 (done as a reference)
M0 is already scaffolded so you have a working example to read. Read these files in order and make
sure you understand every line (chapters 04 and 13 explain the details):
1. `pyproject.toml`: dependencies, dev dependencies, ruff and pytest config.
2. `app/core/config.py`: typed settings from `.env`.
3. `app/api/routes/health.py`: a router with one endpoint.
4. `app/main.py`: the app factory that mounts the router.
5. `tests/test_health.py`: calling the app in a test without starting a server.

Then: `cp .env.example .env`, change `APP_NAME`, restart the server, and watch `/health` reflect it.
