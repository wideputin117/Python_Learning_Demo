"""Chapter 01 exercises: syntax & built-in types.

Replace each `raise NotImplementedError` with your implementation, then run:
    uv run python exercises/ch01_syntax.py
Solutions: exercises/solutions/ch01_syntax.py
"""


def format_ticket_ref(ticket_id: int) -> str:
    """TODO: 42 -> "TCK-00042" (zero-pad to width 5 with an f-string format spec)."""
    raise NotImplementedError


def priority_label(p: int) -> str:
    """TODO: 1 low, 2 medium, 3 high, 4 urgent, anything else "unknown". Use `match`."""
    raise NotImplementedError


def is_blank(text: str | None) -> bool:
    """TODO: True for None, "" or whitespace-only strings."""
    raise NotImplementedError


def confidence_str(score: float) -> str:
    """TODO: 0.875 -> "87.5%" (one decimal, percentage format spec)."""
    raise NotImplementedError


def normalize_tag(tag: str) -> str:
    """TODO: strip, lowercase, spaces -> hyphens. "  Payment Failed " -> "payment-failed"."""
    raise NotImplementedError


if __name__ == "__main__":
    assert format_ticket_ref(42) == "TCK-00042"
    assert format_ticket_ref(123456) == "TCK-123456"

    assert priority_label(1) == "low"
    assert priority_label(4) == "urgent"
    assert priority_label(9) == "unknown"

    assert is_blank(None)
    assert is_blank("")
    assert is_blank("   \n")
    assert not is_blank(" hi ")

    assert confidence_str(0.875) == "87.5%"
    assert confidence_str(1) == "100.0%"

    assert normalize_tag("  Payment Failed ") == "payment-failed"
    assert normalize_tag("BILLING") == "billing"

    print("All ch 01 exercises passed")
