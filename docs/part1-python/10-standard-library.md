# 10 · Standard library essentials

## Concept
Python ships "batteries included". Things you'd `npm install` in Node (path helpers, UUIDs, date maths,
CLI parsing, counters, logging) are already in the **standard library**. Knowing it well saves you from
pulling in dependencies and makes your code look idiomatic. This chapter covers the modules a
backend developer uses every week:

| Module | For |
|---|---|
| `pathlib` | file paths and file I/O |
| `json` | (de)serialising JSON |
| `os` / `os.environ` | env vars, process info |
| `datetime` / `zoneinfo` | timestamps (always timezone-aware!) |
| `logging` | real application logs |
| `collections` | `Counter`, `defaultdict`, `deque`, `namedtuple` |
| `itertools` / `functools` | iteration and function tools |
| `uuid`, `secrets`, `hashlib` | IDs, tokens, hashes |
| `re` | regular expressions |
| `argparse` | small CLI scripts (e.g. `scripts/eval_triage.py`) |

## In Node you'd…
| Node | Python |
|---|---|
| `path.join(__dirname, "data")` | `Path(__file__).parent / "data"` |
| `fs.readFileSync(p, "utf8")` | `Path(p).read_text(encoding="utf-8")` |
| `fs.writeFileSync(p, s)` | `Path(p).write_text(s, encoding="utf-8")` |
| `fs.existsSync(p)` / `fs.mkdirSync(p, {recursive})` | `p.exists()` / `p.mkdir(parents=True, exist_ok=True)` |
| `glob("**/*.md")` package | `Path("docs").rglob("*.md")` |
| `JSON.parse` / `JSON.stringify(o, null, 2)` | `json.loads(s)` / `json.dumps(o, indent=2)` |
| `process.env.KEY` | `os.environ["KEY"]` / `os.environ.get("KEY", "default")` |
| `new Date().toISOString()` | `datetime.now(UTC).isoformat()` |
| dayjs / date-fns | `datetime`, `timedelta`, `zoneinfo` |
| `crypto.randomUUID()` | `uuid.uuid4()` |
| `crypto.randomBytes(32).toString("hex")` | `secrets.token_hex(32)` |
| winston / pino | `logging` (built in) |
| lodash `countBy`, `groupBy` | `Counter`, `defaultdict(list)` |
| lodash `chunk`, `zip`, `flatten` | `itertools.batched`, `zip`, `itertools.chain` |
| yargs / commander | `argparse` |

## Examples

### pathlib: paths as objects
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # like path.resolve(__dirname, "..")
kb_dir = ROOT / "data" / "sample_kb"            # `/` joins paths (works on Windows too)

kb_dir.mkdir(parents=True, exist_ok=True)
faq = kb_dir / "refunds.md"
faq.write_text("# Refunds\nRefunds take 5–7 days.\n", encoding="utf-8")

faq.exists()          # True
faq.name              # 'refunds.md'
faq.stem              # 'refunds'
faq.suffix            # '.md'
faq.parent            # .../data/sample_kb
text = faq.read_text(encoding="utf-8")

for md in sorted(kb_dir.glob("*.md")):          # or .rglob() for recursive
    print(md.name, md.stat().st_size)
```
For big files, stream line by line: `with faq.open(encoding="utf-8") as f: for line in f: …`
Always pass `encoding="utf-8"`. Otherwise the default depends on the OS.

### json
```python
import json

ticket = {"id": 1, "title": "Charged twice", "tags": ["billing"], "resolved": False}

s = json.dumps(ticket)                 # '{"id": 1, ..., "resolved": false}'
json.dumps(ticket, indent=2)           # pretty
json.loads(s)                          # back to dict

# files
Path("ticket.json").write_text(json.dumps(ticket, indent=2), encoding="utf-8")
data = json.loads(Path("ticket.json").read_text(encoding="utf-8"))

# JSONL (one JSON object per line), common for datasets and LLM eval sets
with open("tickets.jsonl", "w", encoding="utf-8") as f:
    for t in [ticket, ticket]:
        f.write(json.dumps(t) + "\n")
rows = [json.loads(line) for line in open("tickets.jsonl", encoding="utf-8")]
```
`json.dumps` fails on `datetime`, `UUID`, sets and custom classes. Either convert them first or use
`default=str`. Pydantic's `.model_dump_json()` (chapter 14) handles all of these for you.

### os.environ
```python
import os

os.environ.get("ANTHROPIC_API_KEY")          # None if missing
os.environ.get("ENVIRONMENT", "development") # with a default
os.environ["JWT_SECRET"]                     # KeyError if missing (fail fast)
```
In TriageDesk you **don't** read `os.environ` directly. `app/core/config.py` (pydantic-settings) does
it once, with types and validation. Use `os.environ` in small scripts only.

### datetime: always timezone-aware, store UTC
```python
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

now = datetime.now(UTC)                      # ✅ aware: 2026-10-12 11:30:00+00:00
datetime.now()                               # ⚠️ naive: no timezone, ambiguous
datetime.utcnow()                            # ❌ deprecated, returns a naive datetime

now.isoformat()                              # '2026-10-12T11:30:00.123456+00:00'
datetime.fromisoformat("2026-10-12T11:30:00+00:00")

sla_deadline = now + timedelta(hours=4)      # urgent tickets: 4h SLA
overdue = datetime.now(UTC) > sla_deadline
age = datetime.now(UTC) - now                # a timedelta
age.total_seconds()

now.astimezone(ZoneInfo("Asia/Kolkata"))     # display in a local time zone
now.strftime("%Y-%m-%d %H:%M")               # format: '2026-10-12 11:30'
```
The rule is to store and compute in UTC and convert only for display, the same as in JS. Unlike JS, though,
naive datetimes exist, and comparing naive with aware raises `TypeError`.

### logging: not print
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)     # one logger per module, named e.g. "app.services.tickets"

logger.debug("not shown at INFO level")
logger.info("ticket created id=%s priority=%s", 42, "high")   # lazy %-formatting
logger.warning("SLA close for ticket %s", 42)
try:
    1 / 0
except ZeroDivisionError:
    logger.exception("triage failed")    # logs at ERROR + full traceback
```
- `basicConfig` is called **once**, at app startup (the entrypoint). Library and module code just calls `getLogger(__name__)`.
- Pass args (`"id=%s", 42`) instead of f-strings, so the formatting only happens if the message is actually emitted.
- Log levels: `DEBUG < INFO < WARNING < ERROR < CRITICAL`.
- Logger names form a hierarchy: `logging.getLogger("app").setLevel(logging.DEBUG)` affects `app.*`.
- Never log secrets (API keys, JWTs, passwords) or full customer messages at INFO level in production.

### collections
```python
from collections import Counter, defaultdict, deque, namedtuple

categories = ["billing", "bug", "billing", "account", "billing"]
c = Counter(categories)
c.most_common(2)          # [('billing', 3), ('bug', 1)]
c["billing"]              # 3
c["nonexistent"]          # 0 (no KeyError)

by_category: defaultdict[str, list[int]] = defaultdict(list)
for ticket_id, cat in enumerate(categories, start=1):
    by_category[cat].append(ticket_id)        # no "if key not in dict" dance
dict(by_category)         # {'billing': [1, 3, 5], 'bug': [2], 'account': [4]}

recent = deque(maxlen=3)  # bounded queue: keeps the last N items
for i in range(5):
    recent.append(i)
recent                    # deque([2, 3, 4])

Point = namedtuple("Point", "x y")   # lightweight immutable record (dataclasses are usually nicer)
```

### itertools and functools
```python
from itertools import batched, chain, groupby, islice, pairwise
from functools import partial, reduce, cache

list(batched(range(7), 3))                   # [(0,1,2), (3,4,5), (6,)]: batch embedding calls
list(chain([1, 2], [3], [4, 5]))             # flatten one level
list(islice(chain.from_iterable(...), 10))   # take the first 10
list(pairwise([1, 2, 3]))                    # [(1,2), (2,3)]

# groupby needs SORTED input (it groups consecutive items)
rows = sorted(tickets, key=lambda t: t["priority"])
for prio, group in groupby(rows, key=lambda t: t["priority"]):
    print(prio, [t["id"] for t in group])

log_error = partial(logger.log, logging.ERROR)   # pre-fill arguments
```

### uuid, secrets, hashlib
```python
import hashlib, secrets, uuid

uuid.uuid4()                 # UUID('3f2b…'): random ID
str(uuid.uuid4())            # as a string
secrets.token_urlsafe(32)    # random token, e.g. for JWT_SECRET or reset links
hashlib.sha256(b"chunk text").hexdigest()   # content hash, e.g. to skip re-embedding unchanged KB chunks
```
`random` is **not** for security. Use `secrets`. Password hashing needs a slow hash (argon2, chapter 17), not sha256.

### re (regular expressions)
```python
import re

ORDER_ID = re.compile(r"\bORD-\d{6}\b")
ORDER_ID.findall("Order ORD-123456 and ORD-654321 are late")   # ['ORD-123456', 'ORD-654321']
m = re.search(r"refund of \$(\d+)", "I want a refund of $40")
m.group(1) if m else None    # '40'
re.sub(r"\s+", " ", "  too   many spaces ").strip()   # 'too many spaces'
```
Use raw strings `r"..."` for patterns, so backslashes aren't interpreted twice.

### argparse: tiny CLIs for scripts
```python
import argparse

parser = argparse.ArgumentParser(description="Evaluate triage accuracy")
parser.add_argument("dataset", type=Path)
parser.add_argument("--limit", type=int, default=50)
parser.add_argument("--verbose", action="store_true")
args = parser.parse_args()        # `uv run python scripts/eval_triage.py data/x.json --limit 10`
```

## Gotchas
- **Naive datetimes.** `datetime.now()` has no timezone. Always use `datetime.now(UTC)`.
- **`json.dumps` can't serialise** `datetime`/`UUID`/`set`. Convert them first, pass `default=str`, or use Pydantic.
- **Forgetting `encoding="utf-8"`** gives you OS-dependent behaviour and mangled emoji or `€`.
- **Calling `logging.basicConfig` in several modules.** Only the first call takes effect. Configure once in the entrypoint.
- **`print` debugging left in code.** Use `logger.debug` instead, so you can turn it on and off.
- **`groupby` on unsorted data** produces repeated groups. Sort first, or just use `defaultdict(list)`.
- **Using `random` for tokens.** Use `secrets`.

## Exercises
Starter file: `exercises/ch10_stdlib.py`. The solution is in `exercises/solutions/ch10_stdlib.py`.

1. `save_tickets(path, tickets)` / `load_tickets(path)`: write and read a JSON file with pathlib. Create parent dirs if needed.
2. `category_report(tickets) -> list[tuple[str, int]]`: the categories sorted by count, descending (use `Counter`).
3. `group_ids_by_priority(tickets) -> dict[str, list[int]]` using `defaultdict`.
4. `sla_deadline(created_at, priority) -> datetime`: urgent = +4h, high = +24h, otherwise +72h. Reject naive datetimes with `ValueError`.
5. `new_ticket_ref() -> str`: `"TCK-"` followed by the first 8 hex characters of a uuid4.

<details><summary>Answers</summary>

```python
import json, uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

def save_tickets(path: Path, tickets: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tickets, indent=2), encoding="utf-8")

def load_tickets(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))

def category_report(tickets):
    return Counter(t["category"] for t in tickets).most_common()

def group_ids_by_priority(tickets):
    groups = defaultdict(list)
    for t in tickets:
        groups[t["priority"]].append(t["id"])
    return dict(groups)

SLA = {"urgent": timedelta(hours=4), "high": timedelta(hours=24)}

def sla_deadline(created_at: datetime, priority: str) -> datetime:
    if created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    return created_at + SLA.get(priority, timedelta(hours=72))

def new_ticket_ref() -> str:
    return f"TCK-{uuid.uuid4().hex[:8]}"
```
</details>

## Apply to TriageDesk: M3 logging
In M3 you'll add `app/core/logging.py` with a `setup_logging(level: str)` function that calls
`logging.basicConfig` (or `logging.config.dictConfig`) once. `create_app()` in `app/main.py` calls it,
and every module does `logger = logging.getLogger(__name__)`. You'll also use:
- `datetime.now(UTC)` for `created_at` / `updated_at` on tickets (M1/M2),
- `pathlib` + `json` to load `data/sample_tickets.json` and `data/sample_kb/*.md` (M5, M8),
- `Counter` for the confusion matrix and accuracy report in `scripts/eval_triage.py` (M8),
- `hashlib` to skip re-embedding unchanged KB documents (M5).
