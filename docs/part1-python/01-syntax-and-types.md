# 01 · Syntax & built-in types

## Concept
Python's syntax is small and strict:
- **Blocks are defined by indentation** (4 spaces) and opened by a colon `:`. There are no braces or semicolons.
- **Variables have no declaration keyword.** `x = 1` creates or rebinds a name. Names point to objects,
  and **objects** have types, not variables (like JS, Python is dynamically typed).
- **Strong typing.** Python never silently coerces between types. `"1" + 1` is a `TypeError`, not `"11"`.
- **Everything is an object**, including `int`, functions, classes and modules.

The built-in scalar types you'll use constantly:

| Type | Example | Notes |
|---|---|---|
| `int` | `42`, `1_000_000`, `0xff` | Arbitrary precision: `2**200` just works. No `BigInt` needed. |
| `float` | `3.14`, `1e-3` | IEEE 754 double, same as JS `number`. |
| `bool` | `True`, `False` | A subclass of `int` (`True + True == 2`). |
| `str` | `"hi"`, `'hi'`, `"""multi"""` | Immutable Unicode text. |
| `None` | `None` | The one "no value". Python has no `undefined`. |
| `bytes` | `b"raw"` | Binary data (like `Buffer`). |

## In Node you'd…
```js
// JavaScript
const title = "Login broken";
let priority = 2;
const isUrgent = priority >= 3 && !title.includes("test");
const msg = `Ticket "${title}" has priority ${priority}`;
if (priority === 1) {
  console.log("low");
} else if (priority === 2) {
  console.log("medium");
} else {
  console.log("high");
}
console.log(7 / 2);          // 3.5
console.log(Math.floor(7 / 2)); // 3
console.log(typeof null);    // "object"  (famous JS quirk)
```
```python
# Python
title = "Login broken"
priority = 2
is_urgent = priority >= 3 and "test" not in title
msg = f'Ticket "{title}" has priority {priority}'
if priority == 1:
    print("low")
elif priority == 2:
    print("medium")
else:
    print("high")
print(7 / 2)      # 3.5  (true division always returns float)
print(7 // 2)     # 3    (floor division)
print(type(None)) # <class 'NoneType'>
```
Things to notice:
- `snake_case` for variables and functions, `PascalCase` for classes, `UPPER_CASE` for constants (PEP 8).
- `and`/`or`/`not` instead of `&&`/`||`/`!`.
- `in` / `not in` for membership: `"test" in title` is the same as `title.includes("test")`.
- There is no `===`. `==` never coerces types: `1 == "1"` is simply `False`.

## Examples

### Numbers
```python
>>> 7 / 2, 7 // 2, 7 % 2, 2 ** 10
(3.5, 3, 1, 1024)
>>> -7 // 2          # floors toward negative infinity, NOT toward zero
-4
>>> int("42"), float("3.5"), str(42)
(42, 3.5, '42')
>>> int("4.2")       # ValueError, so be explicit: int(float("4.2"))
>>> 0.1 + 0.2        # same float issue as JS
0.30000000000000004
>>> round(2.675, 2), round(0.5), round(1.5)   # banker's rounding!
(2.67, 0, 2)
>>> abs(-3), min(3, 1, 2), max([4, 9]), divmod(17, 5)
(3, 1, 9, (3, 2))
```
For money, use `decimal.Decimal("19.99")`, never floats.

### Strings
Strings are immutable sequences. Single and double quotes are equivalent.
```python
>>> s = "  Payment Failed  "
>>> s.strip(), s.lower(), s.upper(), s.strip().replace(" ", "_")
('Payment Failed', '  payment failed  ', '  PAYMENT FAILED  ', 'Payment_Failed')
>>> "a,b,c".split(","), "-".join(["a", "b", "c"])
(['a', 'b', 'c'], 'a-b-c')
>>> "billing".startswith("bill"), "invoice.pdf".endswith((".pdf", ".md"))
(True, True)
>>> "ticket"[0], "ticket"[-1], "ticket"[1:4]       # indexing & slicing (chapter 02)
('t', 't', 'ick')
>>> len("héllo")
5
>>> "ab" * 3
'ababab'
>>> """Multi-line
... string"""
'Multi-line\nstring'
>>> r"C:\new\table"                               # raw string: backslashes are not escapes
'C:\\new\\table'
```
Note the `join` direction: in JS it's `arr.join("-")`, but in Python it's `"-".join(lst)`. The
separator is the object.

### f-strings (template literals, with superpowers)
```python
>>> ticket_id, score, title = 7, 0.91234, "Refund"
>>> f"#{ticket_id:05d}"            # zero-pad to width 5
'#00007'
>>> f"confidence={score:.2f}"      # 2 decimals
'confidence=0.91'
>>> f"{score:.1%}"                 # as percentage
'91.2%'
>>> f"{1234567:,}"                 # thousands separator
'1,234,567'
>>> f"[{title:<10}]|[{title:>10}]|[{title:^10}]"   # align left/right/center
'[Refund    ]|[    Refund]|[  Refund  ]'
>>> f"{title=}  {score=:.2f}"      # debug form: prints name=value
"title='Refund'  score=0.91"
>>> f"{title!r}"                   # repr(), which shows quotes
"'Refund'"
```
The format spec after `:` is `[fill][align][width][,][.precision][type]`. `f"{x=}"` is the
quickest way to debug-print.

### None and truthiness
`None` is a singleton, so compare it with `is`, not `==`:
```python
assignee = None
if assignee is None:
    print("unassigned")
```
**Falsy values:** `None`, `False`, `0`, `0.0`, `""`, and **empty containers** `[]`, `{}`, `set()`, `()`.
Everything else is truthy.

| Value | JS truthy? | Python truthy? |
|---|---|---|
| `[]` / `{}` | ✅ truthy | ❌ falsy |
| `""` | falsy | falsy |
| `0` | falsy | falsy |
| `NaN` | falsy | `float("nan")` is **truthy** |

That's why idiomatic Python is `if tickets:` rather than `if len(tickets) > 0:`.

`and`/`or` return one of their operands, like JS `&&`/`||`:
```python
>>> name = "" or "anonymous"     # like JS ||, NOT like ??
'anonymous'
>>> 0 or 10                      # careful: 0 is falsy
10
```
Python has no `??`. When `0`/`""` are valid values, write it explicitly:
```python
limit = user_limit if user_limit is not None else 20
```

### `is` vs `==`
- `==` asks: are the values equal? It calls `__eq__`.
- `is` asks: is this the same object in memory? (Like comparing references.)
```python
>>> a = [1, 2]; b = [1, 2]
>>> a == b, a is b
(True, False)
```
Use `is` only for `None`, `True`/`False` and sentinel objects. Small ints and short strings may be
*cached*, so `x is 5` sometimes "works" by accident. Never rely on that.

### Conditional expression (ternary)
```python
label = "urgent" if priority >= 3 else "normal"     # JS: priority >= 3 ? "urgent" : "normal"
```

### Chained comparisons
```python
if 1 <= priority <= 4:       # JS: priority >= 1 && priority <= 4
    ...
```

### Loops
```python
for i in range(3):            # 0, 1, 2   (range(start, stop, step))
    print(i)

n = 3
while n > 0:
    n -= 1                    # no ++ / -- in Python

for word in ["a", "b"]:
    if word == "b":
        break
else:                          # runs only if the loop did NOT break (rarely used, but you'll see it)
    print("no break")
```
`pass` is the "do nothing" statement for empty blocks: `if x: pass`.

### The walrus operator `:=`
This assigns inside an expression, which is handy in `while` loops and comprehensions:
```python
if (n := len(title)) > 50:
    print(f"title too long ({n} chars)")
```

### `match`: structural pattern matching (3.10+)
It's a much more powerful `switch`. There's no fall-through and no `break`:
```python
def route(event: dict) -> str:
    match event:
        case {"type": "ticket.created", "priority": "urgent"}:
            return "page on-call"
        case {"type": "ticket.created"}:
            return "queue"
        case {"type": "ticket.closed" | "ticket.deleted"}:
            return "archive"
        case _:
            return "ignore"

route({"type": "ticket.created", "priority": "urgent"})   # 'page on-call'
```
It can also match values (`case 1:`), sequences (`case [first, *rest]:`) and classes
(`case Ticket(status="open"):`).

### Comments & docstrings
```python
# A line comment.

def triage(text: str) -> str:
    """One-line summary of what this does.

    A docstring is the first string in a function/class/module. help() and editors show it.
    """
    return "billing"
```

### Introspecting types
```python
>>> type(3), type(3.0), type("3"), type(True)
(<class 'int'>, <class 'float'>, <class 'str'>, <class 'bool'>)
>>> isinstance(True, int)      # bool is a subclass of int
True
>>> isinstance(3, (int, float))
True
```
Prefer `isinstance(x, T)` over `type(x) == T`, because it respects inheritance.

## Gotchas
- **`"1" + 1` raises `TypeError`.** Convert explicitly: `"1" + str(1)` or `int("1") + 1`.
- **`/` always returns a float** (`4 / 2 == 2.0`). Use `//` for integer division.
- **`-7 // 2 == -4`.** Floor division rounds down, not toward zero (JS `Math.trunc` differs).
- **`round()` uses banker's rounding** (`round(0.5) == 0`).
- **Empty list/dict are falsy**, unlike JS.
- **`x or default` treats `0` and `""` as missing.** Use `if x is None` when that matters.
- **Don't use `is` to compare numbers or strings.** It checks identity, not value.
- **Strings are immutable.** `s[0] = "X"` fails; build a new string instead (`"X" + s[1:]`).
- **No `++`.** Use `i += 1`.
- **Shadowing built-ins:** naming a variable `list`, `dict`, `id`, `type`, `input` or `str` hides the
  built-in. Ruff warns about some of these. `ticket_id` beats `id`.

## Exercises
Starter file: `exercises/ch01_syntax.py`. Fill in the `TODO` functions, then run:
```bash
uv run python exercises/ch01_syntax.py
```
Compare with `exercises/solutions/ch01_syntax.py` when you're done.

1. `format_ticket_ref(ticket_id)` → `"TCK-00042"` for `42` (zero-pad to 5).
2. `priority_label(p)` → `"low"` (1), `"medium"` (2), `"high"` (3), `"urgent"` (4), else `"unknown"`. Use `match`.
3. `is_blank(text)` → `True` for `None`, `""` or whitespace-only strings.
4. `confidence_str(score)` → `"87.5%"` for `0.875`.
5. `normalize_tag(tag)` → strip, lowercase, spaces → hyphens: `"  Payment Failed "` → `"payment-failed"`.

<details><summary>Answers</summary>

```python
def format_ticket_ref(ticket_id: int) -> str:
    return f"TCK-{ticket_id:05d}"

def priority_label(p: int) -> str:
    match p:
        case 1: return "low"
        case 2: return "medium"
        case 3: return "high"
        case 4: return "urgent"
        case _: return "unknown"

def is_blank(text: str | None) -> bool:
    return text is None or not text.strip()

def confidence_str(score: float) -> str:
    return f"{score:.1%}"

def normalize_tag(tag: str) -> str:
    return tag.strip().lower().replace(" ", "-")
```
In `is_blank`, `not text.strip()` works because an empty string is falsy. The `text is None` check
comes first and short-circuits, so `.strip()` is never called on `None`.
</details>

## Apply to TriageDesk
No milestone for this chapter, just practice. Open `app/core/config.py` and find: a `str` default,
a `bool` default, and the `"""docstring"""`. In the REPL, run
`from app.core.config import get_settings; s = get_settings(); print(f"{s.app_name=} {s.debug=}")`.
