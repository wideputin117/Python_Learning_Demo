"""Chapter 10 exercises: standard library essentials.

Run: uv run python exercises/ch10_stdlib.py
Replace each `raise NotImplementedError` with your code until all asserts pass.
"""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path


def save_tickets(path: Path, tickets: list[dict]) -> None:
    """Write tickets as pretty JSON (UTF-8). Create parent directories if needed."""
    raise NotImplementedError


def load_tickets(path: Path) -> list[dict]:
    """Read tickets back from a JSON file."""
    raise NotImplementedError


def category_report(tickets: list[dict]) -> list[tuple[str, int]]:
    """(category, count) pairs sorted by count descending. Hint: collections.Counter."""
    raise NotImplementedError


def group_ids_by_priority(tickets: list[dict]) -> dict[str, list[int]]:
    """{"high": [1, 3], ...}. Hint: collections.defaultdict."""
    raise NotImplementedError


def sla_deadline(created_at: datetime, priority: str) -> datetime:
    """urgent +4h, high +24h, anything else +72h. Raise ValueError for naive datetimes."""
    raise NotImplementedError


def new_ticket_ref() -> str:
    """'TCK-' + first 8 hex chars of a uuid4, e.g. 'TCK-3f2b9a1c'."""
    raise NotImplementedError


if __name__ == "__main__":
    tickets = [
        {"id": 1, "category": "billing", "priority": "high"},
        {"id": 2, "category": "bug", "priority": "low"},
        {"id": 3, "category": "billing", "priority": "high"},
        {"id": 4, "category": "account", "priority": "urgent"},
        {"id": 5, "category": "billing", "priority": "low"},
        {"id": 6, "category": "bug", "priority": "low"},
    ]

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nested" / "dir" / "tickets.json"
        save_tickets(path, tickets)
        assert path.exists()
        assert load_tickets(path) == tickets

    assert category_report(tickets) == [("billing", 3), ("bug", 2), ("account", 1)]

    assert group_ids_by_priority(tickets) == {"high": [1, 3], "low": [2, 5, 6], "urgent": [4]}

    created = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
    assert sla_deadline(created, "urgent") == created + timedelta(hours=4)
    assert sla_deadline(created, "high") == created + timedelta(hours=24)
    assert sla_deadline(created, "low") == created + timedelta(hours=72)
    try:
        sla_deadline(datetime(2026, 10, 12, 9, 0), "high")
        raise AssertionError("naive datetime should be rejected")
    except ValueError:
        pass

    ref = new_ticket_ref()
    assert ref.startswith("TCK-") and len(ref) == 12
    int(ref[4:], 16)  # must be valid hex
    assert new_ticket_ref() != ref

    print("All ch 10 exercises passed")
