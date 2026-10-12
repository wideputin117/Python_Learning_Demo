"""Keyword-based ticket classifier.

TODO 1: import `normalize` from the sibling module `text.py` using a RELATIVE import.
"""

KEYWORDS: dict[str, set[str]] = {
    "billing": {"refund", "invoice", "charge", "charged"},
    "auth": {"login", "password", "2fa"},
}


def classify(text: str) -> str:
    """TODO 2: normalize the text, split into words, return the first category whose keywords
    intersect the words (set &), else "other"."""
    raise NotImplementedError
