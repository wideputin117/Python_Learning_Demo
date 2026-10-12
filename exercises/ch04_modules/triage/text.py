"""Text helpers (already implemented)."""

import re


def normalize(text: str) -> str:
    """Lowercase, replace punctuation with spaces, collapse whitespace."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())
