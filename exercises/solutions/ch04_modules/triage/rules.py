"""Keyword-based ticket classifier."""

from .text import normalize

KEYWORDS: dict[str, set[str]] = {
    "billing": {"refund", "invoice", "charge", "charged"},
    "auth": {"login", "password", "2fa"},
}


def classify(text: str) -> str:
    words = set(normalize(text).split())
    for category, keywords in KEYWORDS.items():
        if words & keywords:
            return category
    return "other"
