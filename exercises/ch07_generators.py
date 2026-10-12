"""Chapter 07 exercises: iterators, generators, context managers.

Run: uv run python exercises/ch07_generators.py
Replace each `raise NotImplementedError` with your code until all asserts pass.
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from itertools import islice


def fibonacci() -> Iterator[int]:
    """Infinite generator: 0, 1, 1, 2, 3, 5, ..."""
    raise NotImplementedError


def chunk_words(text: str, size: int) -> Iterator[list[str]]:
    """Yield lists of `size` words. The last chunk may be shorter."""
    raise NotImplementedError


def read_tickets(lines: Iterable[str]) -> Iterator[str]:
    """Strip whitespace, skip blank lines and lines starting with '#', yield lowercased text."""
    raise NotImplementedError


@contextmanager
def timer() -> Iterator[dict[str, float]]:
    """Yield a dict; on exit (even on error) store elapsed seconds under key 'elapsed'."""
    raise NotImplementedError
    yield {}  # keeps this a generator so @contextmanager works; remove when implementing


if __name__ == "__main__":
    assert list(islice(fibonacci(), 10)) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

    assert list(chunk_words("a b c d e", 2)) == [["a", "b"], ["c", "d"], ["e"]]
    assert list(chunk_words("", 3)) == []

    raw = ["  Login BROKEN ", "", "# internal note", "Refund please\n", "   "]
    assert list(read_tickets(raw)) == ["login broken", "refund please"]
    gen = read_tickets(raw)
    assert iter(gen) is gen, "read_tickets should be a generator (lazy), not return a list"

    with timer() as t:
        sum(range(10_000))
    assert t["elapsed"] >= 0

    t2: dict[str, float] = {}
    try:
        with timer() as t2:
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert "elapsed" in t2, "timer must record elapsed even when the body raises"

    print("All ch 07 exercises passed")
