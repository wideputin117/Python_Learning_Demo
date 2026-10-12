"""Chapter 02 solutions: collections & comprehensions."""

from collections import Counter, defaultdict
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
    return [t["title"] for t in sorted(tickets, key=lambda t: (-t["priority"], t["id"]))]


def count_by_category(tickets: list[Ticket]) -> dict[str, int]:
    return dict(Counter(t["category"] for t in tickets))


def group_ids_by_category(tickets: list[Ticket]) -> dict[str, list[int]]:
    groups: defaultdict[str, list[int]] = defaultdict(list)
    for t in tickets:
        groups[t["category"]].append(t["id"])
    return dict(groups)


def unique_tags(tickets: list[Ticket]) -> list[str]:
    return sorted({tag for t in tickets for tag in t["tags"]})


def paginate(items: list[Any], page: int, size: int) -> list[Any]:
    start = (page - 1) * size
    return items[start : start + size]


def first_urgent(tickets: list[Ticket]) -> Ticket | None:
    return next((t for t in tickets if t["priority"] >= 4), None)


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
