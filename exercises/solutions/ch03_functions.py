"""Chapter 03 solutions: functions, args, closures, scope."""

from collections.abc import Callable
from typing import Any


def priority_score(urgency: int, impact: int, *, vip: bool = False) -> int:
    return urgency * impact + (4 if vip else 0)


def add_watcher(name: str, watchers: list[str] | None = None) -> list[str]:
    if watchers is None:
        watchers = []
    watchers.append(name)
    return watchers


def make_counter() -> Callable[[], int]:
    count = 0

    def counter() -> int:
        nonlocal count
        count += 1
        return count

    return counter


def build_query(**filters: object) -> str:
    return "&".join(f"{k}={v}" for k, v in sorted(filters.items()) if v is not None)


def apply_all(value: Any, *funcs: Callable[[Any], Any]) -> Any:
    for f in funcs:
        value = f(value)
    return value


if __name__ == "__main__":
    assert priority_score(3, 4) == 12
    assert priority_score(2, 2, vip=True) == 8
    try:
        priority_score(2, 2, True)  # type: ignore[misc]
    except TypeError:
        pass
    else:
        raise AssertionError("vip must be keyword-only")

    assert add_watcher("ana") == ["ana"]
    assert add_watcher("bo") == ["bo"], "default list is being shared between calls"
    existing = ["cy"]
    assert add_watcher("di", existing) == ["cy", "di"]

    c1, c2 = make_counter(), make_counter()
    assert [c1(), c1(), c1()] == [1, 2, 3]
    assert c2() == 1, "counters must be independent"

    assert build_query(priority=3, category="billing", agent=None) == "category=billing&priority=3"
    assert build_query() == ""

    assert apply_all(" Hi ", str.strip, str.lower) == "hi"
    assert apply_all(5) == 5

    print("All ch 03 exercises passed")
