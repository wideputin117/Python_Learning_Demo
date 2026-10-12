"""Chapter 09 exercises: type hints.

Run: uv run python exercises/ch09_types.py
1. Fill in the TODO types (they currently use Any; replace them with precise hints).
2. Replace each `raise NotImplementedError` until all asserts pass.
Optional: uv add --dev pyright && uv run pyright exercises/ch09_types.py
"""

from typing import Any, Protocol

# TODO: make this a Literal of "low", "medium", "high", "urgent"
type Priority = Any


# TODO: make this a TypedDict with id: int, title: str, priority: Priority, optional tags: list[str]
TicketDict = dict


def first(items):  # TODO: make generic: def first[T](items: list[T]) -> T | None
    """Return the first item, or None if the list is empty."""
    raise NotImplementedError


def by_priority(tickets, priority):  # TODO: add hints
    """Return only the tickets with the given priority."""
    raise NotImplementedError


class Notifier(Protocol):
    # TODO: declare `send(self, to: str, message: str) -> bool`
    pass


class FakeNotifier:
    """Records every message instead of sending it. Satisfies Notifier structurally."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, to: str, message: str) -> bool:
        raise NotImplementedError


def notify_all(notifier, tickets) -> int:  # TODO: hint notifier as Notifier
    """Send f"#{id}: {title}" to "agents" for each ticket; return number of successful sends."""
    raise NotImplementedError


if __name__ == "__main__":
    tickets: list[TicketDict] = [
        {"id": 1, "title": "Login broken", "priority": "high"},
        {"id": 2, "title": "Change email", "priority": "low", "tags": ["account"]},
        {"id": 3, "title": "Charged twice", "priority": "high", "tags": ["billing"]},
    ]

    assert first([10, 20]) == 10
    assert first([]) is None

    assert [t["id"] for t in by_priority(tickets, "high")] == [1, 3]
    assert by_priority(tickets, "urgent") == []

    fake = FakeNotifier()
    assert notify_all(fake, tickets) == 3
    assert fake.sent[0] == ("agents", "#1: Login broken")

    print("All ch 09 exercises passed")
