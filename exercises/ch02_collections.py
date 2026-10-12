"""Chapter 02 exercises: collections & comprehensions.

Replace each `raise NotImplementedError` with your implementation, then run:
    uv run python exercises/ch02_collections.py
Solutions: exercises/solutions/ch02_collections.py
"""

from typing import Any

Ticket = dict[str, Any]

TICKETS: list[Ticket] = [
    {
        "id": 1,
        "title": "Refund not received",
        "priority": 3,
        "category": "billing",
        "tags": ["refund", "payment"],
    },
    {"id": 2, "title": "Cannot log in", "priority": 4, "category": "auth", "tags": ["login"]},
    {
        "id": 3,
        "title": "Invoice wrong",
        "priority": 3,
        "category": "billing",
        "tags": ["invoice", "payment"],
    },
    {"id": 4, "title": "Feature idea", "priority": 1, "category": "feedback", "tags": []},
]


def titles_by_priority(tickets: list[Ticket]) -> list[str]:
    """TODO: titles sorted by priority DESC, then id ASC (hint: sorted + key with a tuple)."""
    raise NotImplementedError


def count_by_category(tickets: list[Ticket]) -> dict[str, int]:
    """TODO: {"billing": 2, ...}. Try collections.Counter."""
    raise NotImplementedError


def group_ids_by_category(tickets: list[Ticket]) -> dict[str, list[int]]:
    """TODO: {"billing": [1, 3], ...}. Try collections.defaultdict(list)."""
    raise NotImplementedError


def unique_tags(tickets: list[Ticket]) -> list[str]:
    """TODO: sorted list of distinct tags (hint: a nested set comprehension)."""
    raise NotImplementedError


def paginate(items: list[Any], page: int, size: int) -> list[Any]:
    """TODO: 1-based page of `size` items, using slicing."""
    raise NotImplementedError


def first_urgent(tickets: list[Ticket]) -> Ticket | None:
    """TODO: first ticket with priority >= 4, or None (hint: next() with a default)."""
    raise NotImplementedError


if __name__ == "__main__":
    assert titles_by_priority(TICKETS) == [
        "Cannot log in",
        "Refund not received",
        "Invoice wrong",
        "Feature idea",
    ]
    assert count_by_category(TICKETS) == {"billing": 2, "auth": 1, "feedback": 1}
    assert group_ids_by_category(TICKETS) == {"billing": [1, 3], "auth": [2], "feedback": [4]}
    assert unique_tags(TICKETS) == ["invoice", "login", "payment", "refund"]

    items = list(range(1, 11))
    assert paginate(items, 1, 3) == [1, 2, 3]
    assert paginate(items, 4, 3) == [10]
    assert paginate(items, 5, 3) == []

    urgent = first_urgent(TICKETS)
    assert urgent is not None and urgent["id"] == 2
    assert first_urgent([t for t in TICKETS if t["priority"] < 4]) is None

    print("All ch 02 exercises passed")
