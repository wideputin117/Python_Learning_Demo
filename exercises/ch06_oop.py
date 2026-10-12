"""Chapter 06 exercises: classes, dataclasses, enums (M1 prep).

Fill in the TODOs, then run:
    uv run python exercises/ch06_oop.py
Solutions: exercises/solutions/ch06_oop.py
"""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum


class TicketStatus(StrEnum):
    """TODO: members OPEN="open", IN_PROGRESS="in_progress", RESOLVED="resolved", CLOSED="closed".

    Add a property `is_terminal` -> True for RESOLVED and CLOSED.
    """


class Priority(IntEnum):
    """TODO: LOW=1, MEDIUM=2, HIGH=3, URGENT=4."""


@dataclass
class Ticket:
    """TODO: fields id, title, description, status (default OPEN), priority (default MEDIUM),
    tags (default empty list, so use field(default_factory=...)), created_at (default now in UTC).

    __post_init__: raise ValueError if title is blank.
    """

    def close(self) -> None:
        """TODO: set status CLOSED; raise ValueError if already terminal."""
        raise NotImplementedError

    def is_overdue(self, now: datetime, sla_hours: int) -> bool:
        """TODO: True if not terminal and (now - created_at) > sla_hours."""
        raise NotImplementedError


class TicketStore:
    """TODO: in-memory store.

    add(title, description, priority=Priority.MEDIUM) -> Ticket   (auto-increment ids from 1)
    get(ticket_id) -> Ticket                                      (KeyError if missing)
    list_tickets(status=None) -> list[Ticket]                     (filter by status if given)
    __len__, __contains__(ticket_id)
    """


if __name__ == "__main__":
    from datetime import UTC

    assert hasattr(TicketStatus, "OPEN"), "TODO 1: define TicketStatus members"
    assert hasattr(Priority, "LOW"), "TODO 2: define Priority members"

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
