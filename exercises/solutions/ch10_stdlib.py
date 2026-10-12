"""Chapter 10 solutions: standard library essentials."""

import json
import tempfile
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

SLA = {"urgent": timedelta(hours=4), "high": timedelta(hours=24)}
DEFAULT_SLA = timedelta(hours=72)


def save_tickets(path: Path, tickets: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tickets, indent=2), encoding="utf-8")


def load_tickets(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def category_report(tickets: list[dict]) -> list[tuple[str, int]]:
    return Counter(t["category"] for t in tickets).most_common()


def group_ids_by_priority(tickets: list[dict]) -> dict[str, list[int]]:
    groups: defaultdict[str, list[int]] = defaultdict(list)
    for t in tickets:
        groups[t["priority"]].append(t["id"])
    return dict(groups)


def sla_deadline(created_at: datetime, priority: str) -> datetime:
    if created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    return created_at + SLA.get(priority, DEFAULT_SLA)


def new_ticket_ref() -> str:
    return f"TCK-{uuid.uuid4().hex[:8]}"


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
    int(ref[4:], 16)
    assert new_ticket_ref() != ref

    print("All ch 10 exercises passed")
