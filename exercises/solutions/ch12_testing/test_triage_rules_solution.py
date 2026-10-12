"""Chapter 12 solutions. Run: uv run pytest exercises/solutions/ch12_testing -v"""

from unittest.mock import Mock

import pytest
from triage_rules import TicketQueue, confidence_threshold, guess_priority, triage


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Checkout is DOWN", "urgent"),
        ("Outage in EU region", "urgent"),
        ("I was charged twice", "high"),
        ("Please REFUND me", "high"),
        ("Found a bug in export", "medium"),
        ("Can I get dark mode?", "low"),
    ],
)
def test_guess_priority(text: str, expected: str) -> None:
    assert guess_priority(text) == expected


@pytest.fixture
def queue() -> TicketQueue:
    q = TicketQueue()
    q.add({"id": 1, "priority": "low"})
    q.add({"id": 2, "priority": "urgent"})
    q.add({"id": 3, "priority": "high"})
    return q


def test_queue_returns_highest_priority_first(queue: TicketQueue) -> None:
    assert [queue.next()["id"] for _ in range(3)] == [2, 3, 1]
    assert len(queue) == 0


def test_queue_is_fifo_within_same_priority() -> None:
    q = TicketQueue()
    q.add({"id": 10, "priority": "high"})
    q.add({"id": 11, "priority": "high"})
    assert q.next()["id"] == 10
    assert q.next()["id"] == 11


def test_invalid_priority_rejected() -> None:
    with pytest.raises(ValueError, match="invalid priority"):
        TicketQueue().add({"id": 1, "priority": "asap"})


def test_next_on_empty_queue_raises() -> None:
    with pytest.raises(IndexError):
        TicketQueue().next()


def test_triage_returns_llm_category() -> None:
    llm = Mock()
    llm.classify.return_value = "billing"

    assert triage("refund please", llm) == "billing"
    llm.classify.assert_called_once_with("refund please")


def test_triage_falls_back_when_llm_fails() -> None:
    llm = Mock()
    llm.classify.side_effect = ConnectionError("API down")

    assert triage("anything", llm) == "general"


def test_confidence_threshold_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRIAGE_CONFIDENCE", raising=False)
    assert confidence_threshold() == pytest.approx(0.7)


def test_confidence_threshold_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRIAGE_CONFIDENCE", "0.9")
    assert confidence_threshold() == pytest.approx(0.9)
