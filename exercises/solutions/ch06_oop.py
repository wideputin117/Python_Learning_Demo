"""Chapter 06 solutions: classes, dataclasses, enums (M1 prep)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import IntEnum, StrEnum


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

    @property
    def is_terminal(self) -> bool:
        return self in (TicketStatus.RESOLVED, TicketStatus.CLOSED)


class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Ticket:
    id: int
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: Priority = Priority.MEDIUM
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title must not be blank")

    def close(self) -> None:
        if self.status.is_terminal:
            raise ValueError(f"ticket {self.id} is already {self.status}")
        self.status = TicketStatus.CLOSED

    def is_overdue(self, now: datetime, sla_hours: int) -> bool:
        return not self.status.is_terminal and now - self.created_at > timedelta(hours=sla_hours)


class TicketStore:
    """In-memory ticket repository (the shape M1 will use)."""

    def __init__(self) -> None:
        self._tickets: dict[int, Ticket] = {}
        self._next_id = 1

    def add(self, title: str, description: str, priority: Priority = Priority.MEDIUM) -> Ticket:
        ticket = Ticket(id=self._next_id, title=title, description=description, priority=priority)
        self._tickets[ticket.id] = ticket
        self._next_id += 1
        return ticket

    def get(self, ticket_id: int) -> Ticket:
        return self._tickets[ticket_id]

    def list_tickets(self, status: TicketStatus | None = None) -> list[Ticket]:
        return [t for t in self._tickets.values() if status is None or t.status == status]

    def __len__(self) -> int:
        return len(self._tickets)

    def __contains__(self, ticket_id: object) -> bool:
        return ticket_id in self._tickets


if __name__ == "__main__":
    # 1. TicketStatus
    assert TicketStatus("open") is TicketStatus.OPEN
    assert TicketStatus.IN_PROGRESS == "in_progress"
    assert TicketStatus.CLOSED.is_terminal and not TicketStatus.OPEN.is_terminal

    # 2. Priority
    assert Priority.URGENT > Priority.HIGH > Priority.MEDIUM > Priority.LOW
    assert Priority(3) is Priority.HIGH

    # 3. Ticket dataclass
    t = Ticket(id=1, title="Refund", description="Charged twice")
    assert t.status is TicketStatus.OPEN and t.priority is Priority.MEDIUM
    assert t.tags == [] and t.created_at.tzinfo is not None
    t2 = Ticket(id=2, title="Login", description="2FA broken")
    t.tags.append("billing")
    assert t2.tags == [], "tags default must not be shared"
    try:
        Ticket(id=3, title="   ", description="x")
    except ValueError:
        pass
    else:
        raise AssertionError("blank title should raise ValueError")

    # 4. close()
    t.close()
    assert t.status is TicketStatus.CLOSED
    try:
        t.close()
    except ValueError:
        pass
    else:
        raise AssertionError("closing a closed ticket should raise")

    # 5. is_overdue()
    old = Ticket(id=4, title="Old", description="x", created_at=datetime(2026, 1, 1, tzinfo=UTC))
    now = datetime(2026, 1, 2, 12, tzinfo=UTC)
    assert old.is_overdue(now, sla_hours=24)
    assert not old.is_overdue(now, sla_hours=48)
    old.status = TicketStatus.RESOLVED
    assert not old.is_overdue(now, sla_hours=24), "terminal tickets are never overdue"

    # 6. TicketStore
    store = TicketStore()
    a = store.add("Refund", "Charged twice", priority=Priority.HIGH)
    b = store.add("Login", "2FA broken")
    assert (a.id, b.id) == (1, 2)
    assert len(store) == 2 and 1 in store and 99 not in store
    assert store.get(2) is b
    b.close()
    assert store.list_tickets() == [a, b]
    assert store.list_tickets(status=TicketStatus.OPEN) == [a]
    try:
        store.get(99)
    except KeyError:
        pass
    else:
        raise AssertionError("missing id should raise KeyError")

    print("All ch 06 exercises passed")
