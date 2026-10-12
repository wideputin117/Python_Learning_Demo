# 02 · Collections & comprehensions

## Concept
Python has four core built-in collections. You'll use all of them daily:

| Type | Literal | Mutable? | Ordered? | JS closest |
|---|---|---|---|---|
| `list` | `[1, 2, 3]` | ✅ | ✅ | `Array` |
| `tuple` | `(1, 2, 3)` or `1, 2, 3` | ❌ | ✅ | a frozen array / TS tuple `[string, number]` |
| `dict` | `{"a": 1}` | ✅ | ✅ (insertion order, guaranteed since 3.7) | `Object` / `Map` |
| `set` | `{1, 2, 3}` | ✅ | ❌ | `Set` |

(Plus `frozenset`, the immutable set.) The `collections` module adds `Counter`, `defaultdict`,
`deque` and `namedtuple`.

**Comprehensions** are Python's replacement for `.map()` / `.filter()` chains. They're the single most
idiomatic Python feature, so get comfortable with them.

## In Node you'd…
```js
const tickets = [
  { id: 1, title: "Refund", priority: 3, category: "billing", tags: ["billing"] },
  { id: 2, title: "Login", priority: 1, category: "auth", tags: ["auth"] },
];
const urgentTitles = tickets.filter(t => t.priority >= 3).map(t => t.title);
const byId = Object.fromEntries(tickets.map(t => [t.id, t]));
const allTags = new Set(tickets.flatMap(t => t.tags));
const [first, ...rest] = tickets;
const sorted = [...tickets].sort((a, b) => b.priority - a.priority);
```
```python
tickets = [
    {"id": 1, "title": "Refund", "priority": 3, "category": "billing", "tags": ["billing"]},
    {"id": 2, "title": "Login", "priority": 1, "category": "auth", "tags": ["auth"]},
]
urgent_titles = [t["title"] for t in tickets if t["priority"] >= 3]
by_id = {t["id"]: t for t in tickets}
all_tags = {tag for t in tickets for tag in t["tags"]}
first, *rest = tickets
sorted_tickets = sorted(tickets, key=lambda t: t["priority"], reverse=True)
```
Dict keys are accessed with `d["key"]`, not `d.key`. Attribute access is for objects (chapter 06). In
real code we'll mostly use typed objects (dataclasses/Pydantic) rather than raw dicts.

## Examples

### Lists
```python
>>> q = ["t1", "t2"]
>>> q.append("t3"); q.insert(0, "t0"); q.extend(["t4", "t5"])
>>> q
['t0', 't1', 't2', 't3', 't4', 't5']
>>> q.pop(), q.pop(0)            # pop last / pop index
('t5', 't0')
>>> q.remove("t2")               # remove first matching value (ValueError if absent)
>>> q.index("t3"), "t1" in q, len(q)
(1, True, 3)
>>> q + ["x"], q * 2             # concatenation / repetition (new lists)
>>> q.sort(); q.reverse()        # in place, return None!
>>> sorted(q), list(reversed(q)) # return new lists
```

### Slicing: `seq[start:stop:step]`
This works on lists, tuples and strings. `stop` is exclusive, and negative indexes count from the end.
```python
>>> nums = [0, 1, 2, 3, 4, 5]
>>> nums[1:4], nums[:2], nums[-2:], nums[::2], nums[::-1]
([1, 2, 3], [0, 1], [4, 5], [0, 2, 4], [5, 4, 3, 2, 1, 0])
>>> nums[100:]          # slicing never raises IndexError
[]
>>> nums[:] # shallow copy (like [...arr])
```
Pagination is just slicing: `items[offset : offset + limit]`.

### Tuples & unpacking
Tuples are immutable sequences, used for fixed-shape records and multiple return values.
```python
point = (3, 4)
x, y = point                      # destructuring
a, b = b, a                       # swap without temp
first, *middle, last = [1, 2, 3, 4, 5]   # middle == [2, 3, 4]
single = (1,)                     # one-element tuple needs the comma! (1) is just 1

def min_max(xs: list[int]) -> tuple[int, int]:
    return min(xs), max(xs)       # returns a tuple
lo, hi = min_max([5, 2, 9])
```
Tuples are **hashable** (if their contents are), so they can be dict keys or set members. Lists can't.

### Dicts
```python
>>> counts = {"billing": 3, "auth": 1}
>>> counts["billing"]                 # KeyError if missing!
3
>>> counts.get("shipping"), counts.get("shipping", 0)   # safe access
(None, 0)
>>> counts["shipping"] = 2            # insert/update
>>> del counts["auth"]                # delete (KeyError if missing)
>>> counts.pop("nope", None)          # delete with default, no error
>>> "billing" in counts               # checks KEYS
True
>>> list(counts.keys()), list(counts.values()), list(counts.items())
(['billing', 'shipping'], [3, 2], [('billing', 3), ('shipping', 2)])
>>> for category, n in counts.items():
...     print(f"{category}: {n}")
>>> counts.setdefault("refund", 0)    # get, or insert default and return it
>>> merged = counts | {"auth": 5}     # merge → new dict (3.9+), like {...a, ...b}
>>> counts |= {"auth": 5}             # merge in place
>>> {**counts, "auth": 7}             # spread syntax also works
```
Keys can be any **hashable** value: `str`, `int`, `tuple`, and frozen dataclasses. In JS, object keys
are always strings, so `{1: "a"}` keeps the int `1` here, and `d[1]` and `d["1"]` are different.

### Sets
```python
>>> a = {"billing", "auth", "bug"}
>>> b = {"bug", "feature"}
>>> a | b, a & b, a - b, a ^ b        # union, intersection, difference, symmetric diff
>>> a.add("refund"); a.discard("nope")  # discard: no error if missing (remove raises)
>>> "auth" in a                        # O(1) membership, so use sets for lookups
>>> empty = set()                      # NOT {} which is an empty dict!
>>> list(dict.fromkeys(["b", "a", "b"]))   # dedupe while KEEPING order
['b', 'a']
```

### Comprehensions
```python
squares = [n * n for n in range(5)]                         # list
evens = [n for n in range(10) if n % 2 == 0]                # with filter
labels = ["hi" if p >= 3 else "lo" for p in [1, 3]]         # if/else goes BEFORE for
by_id = {t["id"]: t["title"] for t in tickets}              # dict
cats = {t["category"] for t in tickets}                     # set
pairs = [(c, p) for c in ["a", "b"] for p in [1, 2]]        # nested = flatMap
total = sum(t["priority"] for t in tickets)                 # generator expression (no brackets)
```
Read the nested form left to right as nested `for` loops. Keep comprehensions to one or two clauses,
and if it gets hard to read, write a normal loop.

### Built-ins that replace array methods
| JS | Python |
|---|---|
| `arr.map(f)` | `[f(x) for x in xs]` (or `map(f, xs)`) |
| `arr.filter(f)` | `[x for x in xs if f(x)]` |
| `arr.reduce((a,b)=>a+b, 0)` | `sum(xs)` (or `functools.reduce`) |
| `arr.some(f)` / `arr.every(f)` | `any(f(x) for x in xs)` / `all(...)` |
| `arr.find(f)` | `next((x for x in xs if f(x)), None)` |
| `arr.forEach((x,i)=>…)` | `for i, x in enumerate(xs):` |
| zip two arrays | `for a, b in zip(xs, ys):` |
| `arr.includes(x)` | `x in xs` |
| `arr.flat()` | `[y for x in xs for y in x]` |
| `Math.max(...arr)` | `max(xs)`, `max(xs, key=len)` |

```python
>>> tickets.sort(key=lambda t: (-t["priority"], t["id"]))   # multi-key sort: priority desc, id asc
>>> from operator import itemgetter
>>> sorted(tickets, key=itemgetter("priority"))
>>> for i, title in enumerate(["a", "b"], start=1): print(i, title)
>>> dict(zip(["a", "b"], [1, 2]))
{'a': 1, 'b': 2}
```
`sort` is **stable** and compares with `<`, so there's no `(a, b) => a - b` comparator.
You give a `key` function instead.

### `collections` goodies
```python
from collections import Counter, defaultdict, deque

Counter(["billing", "auth", "billing"]).most_common(1)   # [('billing', 2)]

by_cat: defaultdict[str, list[int]] = defaultdict(list)
for t in tickets:
    by_cat[t["category"]].append(t["id"])     # no "if key not in dict" dance

queue = deque(maxlen=100)    # fast appends/pops at both ends; also a ring buffer
queue.append("t1"); queue.appendleft("t0"); queue.popleft()
```

### Copying vs aliasing
Assignment never copies. It binds another name to the **same object** (same as JS references):
```python
>>> a = [1, 2, 3]
>>> b = a
>>> b.append(4)
>>> a
[1, 2, 3, 4]          # a changed too

>>> c = a.copy()      # or list(a), a[:]: shallow copy
>>> import copy
>>> nested = [[1], [2]]
>>> shallow = nested.copy(); shallow[0].append(99)
>>> nested
[[1, 99], [2]]        # inner lists are shared!
>>> deep = copy.deepcopy(nested)    # like structuredClone
```

## Gotchas
- **`{}` is an empty dict**, not a set. Use `set()`.
- **`list.sort()` returns `None`.** `xs = xs.sort()` wipes your list. Use `sorted(xs)` for a new list.
- **`d["missing"]` raises `KeyError`.** Use `.get()` when absence is normal.
- **`(1)` is not a tuple**, but `(1,)` is.
- **Don't mutate a list or dict while iterating over it.** Iterate over a copy (`for k in list(d):`) or build a new one.
- **`[[]] * 3` creates three references to the same inner list.** Use `[[] for _ in range(3)]`.
- **`in` on a list is O(n), but on a set/dict it's O(1).** Convert to a set for repeated lookups.
- **Dict keys must be hashable.** Lists and dicts can't be keys; tuples can.

## Exercises
Starter file: `exercises/ch02_collections.py`. Run `uv run python exercises/ch02_collections.py`.

1. `titles_by_priority(tickets)`: titles sorted by priority desc, then id asc.
2. `count_by_category(tickets)`: `{"billing": 2, "auth": 1}`. Try both `Counter` and a dict comprehension.
3. `group_ids_by_category(tickets)`: `{"billing": [1, 3], "auth": [2]}` (using `defaultdict`).
4. `unique_tags(tickets)`: sorted list of all distinct tags.
5. `paginate(items, page, size)`: 1-based pages, using slicing.
6. `first_urgent(tickets)`: the first ticket with priority ≥ 4, or `None` (`next(...)`).

<details><summary>Answers</summary>

```python
from collections import Counter, defaultdict

def titles_by_priority(tickets):
    return [t["title"] for t in sorted(tickets, key=lambda t: (-t["priority"], t["id"]))]

def count_by_category(tickets):
    return dict(Counter(t["category"] for t in tickets))

def group_ids_by_category(tickets):
    groups = defaultdict(list)
    for t in tickets:
        groups[t["category"]].append(t["id"])
    return dict(groups)

def unique_tags(tickets):
    return sorted({tag for t in tickets for tag in t["tags"]})

def paginate(items, page, size):
    start = (page - 1) * size
    return items[start : start + size]

def first_urgent(tickets):
    return next((t for t in tickets if t["priority"] >= 4), None)
```
</details>

## Apply to TriageDesk
No milestone yet. In M1 you'll keep tickets in an in-memory `dict[int, Ticket]` and implement
list/filter/paginate. Exercises 1, 5 and 6 are exactly that logic. Keep your solutions handy.
