"""Chapter 09 solutions: type hints."""

from typing import Literal, NotRequired, Protocol, TypedDict

type Priority = Literal["low", "medium", "high", "urgent"]


class TicketDict(TypedDict):
    id: int
    title: str
    priority: Priority
    tags: NotRequired[list[str]]


def first[T](items: list[T]) -> T | None:
    return items[0] if items else None


def by_priority(tickets: list[TicketDict], priority: Priority) -> list[TicketDict]:
    return [t for t in tickets if t["priority"] == priority]


class Notifier(Protocol):
    def send(self, to: str, message: str) -> bool: ...


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, to: str, message: str) -> bool:
        self.sent.append((to, message))
        return True


def notify_all(notifier: Notifier, tickets: list[TicketDict]) -> int:
    return sum(notifier.send("agents", f"#{t['id']}: {t['title']}") for t in tickets)


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
