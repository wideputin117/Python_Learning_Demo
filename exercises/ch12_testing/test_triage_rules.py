"""Chapter 12 exercises: write the tests.

Run: uv run pytest exercises/ch12_testing -v
Replace every `pytest.fail("TODO ...")` with a real test. Add more tests freely.
"""

from unittest.mock import Mock  # noqa: F401  (you'll need it for exercise 4)

import pytest
from triage_rules import TicketQueue, confidence_threshold, guess_priority, triage  # noqa: F401


# 1. Parametrize over at least 5 (text, expected) pairs, including mixed case.
def test_guess_priority() -> None:
    pytest.fail("TODO 1: turn this into a @pytest.mark.parametrize test")


# 2. Write a `queue` fixture holding 3 tickets with different priorities,
#    then check next() hands them out urgent -> high -> ... order.
def test_queue_returns_highest_priority_first() -> None:
    pytest.fail("TODO 2: add a `queue` fixture and use it here")


def test_queue_is_fifo_within_same_priority() -> None:
    pytest.fail("TODO 2b: two 'high' tickets come out in insertion order")


# 3. pytest.raises with match=
def test_invalid_priority_rejected() -> None:
    pytest.fail(
        "TODO 3: adding {'priority': 'asap'} raises ValueError mentioning 'invalid priority'"
    )


def test_next_on_empty_queue_raises() -> None:
    pytest.fail("TODO 3b: next() on an empty queue raises IndexError")


# 4. Mock the LLM
def test_triage_returns_llm_category() -> None:
    pytest.fail("TODO 4: Mock() llm, return_value 'billing', assert_called_once_with the text")


def test_triage_falls_back_when_llm_fails() -> None:
    pytest.fail("TODO 4b: side_effect=ConnectionError -> 'general'")


# 5. monkeypatch env vars
def test_confidence_threshold_default() -> None:
    pytest.fail("TODO 5: delenv TRIAGE_CONFIDENCE (raising=False) -> 0.7")


def test_confidence_threshold_from_env() -> None:
    pytest.fail("TODO 5b: setenv TRIAGE_CONFIDENCE=0.9 -> 0.9")
