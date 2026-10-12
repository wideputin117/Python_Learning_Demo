"""Chapter 03 exercises: functions, args, closures, scope.

Replace each `raise NotImplementedError` (and fix the buggy function), then run:
    uv run python exercises/ch03_functions.py
Solutions: exercises/solutions/ch03_functions.py
"""

from collections.abc import Callable
from typing import Any


def priority_score(urgency: int, impact: int, vip: bool = False) -> int:
    """TODO: return urgency * impact, +4 if vip. ALSO make `vip` keyword-only."""
    raise NotImplementedError


def add_watcher(name: str, watchers: list[str] = []) -> list[str]:  # noqa: B006 (intentional bug)
    """TODO: this has the mutable-default bug. Fix the signature and body."""
    watchers.append(name)
    return watchers


def make_counter() -> Callable[[], int]:
    """TODO: return a function that returns 1, 2, 3... on successive calls (use nonlocal)."""
    raise NotImplementedError


def build_query(**filters: object) -> str:
    """TODO: build a query string, skipping None values, keys sorted alphabetically.

    build_query(priority=3, category="billing", agent=None) -> "category=billing&priority=3"
    """
    raise NotImplementedError


def apply_all(value: Any, *funcs: Callable[[Any], Any]) -> Any:
    """TODO: apply each func in order. apply_all(" Hi ", str.strip, str.lower) -> "hi"."""
    raise NotImplementedError


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
