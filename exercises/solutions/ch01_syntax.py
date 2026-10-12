"""Chapter 01 solutions: syntax & built-in types."""


def format_ticket_ref(ticket_id: int) -> str:
    return f"TCK-{ticket_id:05d}"


def priority_label(p: int) -> str:
    match p:
        case 1:
            return "low"
        case 2:
            return "medium"
        case 3:
            return "high"
        case 4:
            return "urgent"
        case _:
            return "unknown"


def is_blank(text: str | None) -> bool:
    return text is None or not text.strip()


def confidence_str(score: float) -> str:
    return f"{score:.1%}"


def normalize_tag(tag: str) -> str:
    return tag.strip().lower().replace(" ", "-")


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
