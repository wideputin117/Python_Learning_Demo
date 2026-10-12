"""Code under test for the chapter 12 exercises. It's complete, so read it and don't change it.

The tests live in test_triage_rules.py next to this file.
"""

import os
from typing import Protocol

PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


def guess_priority(text: str) -> str:
    """Cheap keyword rules, used before (or instead of) asking an LLM."""
    text = text.lower()
    if "down" in text or "outage" in text:
        return "urgent"
    if "refund" in text or "charged" in text:
        return "high"
    if "bug" in text or "error" in text:
        return "medium"
    return "low"


class TicketQueue:
    """Hands out tickets by priority (urgent first); ties are first-in-first-out."""

    def __init__(self) -> None:
        self._items: list[tuple[int, int, dict]] = []
        self._counter = 0

    def add(self, ticket: dict) -> None:
        priority = ticket.get("priority")
        if priority not in PRIORITY_ORDER:
            raise ValueError(
                f"invalid priority {priority!r}; expected one of {list(PRIORITY_ORDER)}"
            )
        self._items.append((PRIORITY_ORDER[priority], self._counter, ticket))
        self._counter += 1

    def next(self) -> dict:
        if not self._items:
            raise IndexError("queue is empty")
        self._items.sort(key=lambda item: (item[0], item[1]))
        return self._items.pop(0)[2]

    def __len__(self) -> int:
        return len(self._items)


class Classifier(Protocol):
    def classify(self, text: str) -> str: ...


def triage(text: str, llm: Classifier) -> str:
    """Ask the LLM for a category; fall back to "general" if the call fails."""
    try:
        return llm.classify(text)
    except Exception:
        return "general"


def confidence_threshold() -> float:
    """Read TRIAGE_CONFIDENCE from the environment (default 0.7)."""
    return float(os.environ.get("TRIAGE_CONFIDENCE", "0.7"))
