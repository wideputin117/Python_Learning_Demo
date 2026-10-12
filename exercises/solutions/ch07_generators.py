"""Chapter 07 solutions: iterators, generators, context managers."""

import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from itertools import islice


def fibonacci() -> Iterator[int]:
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


def chunk_words(text: str, size: int) -> Iterator[list[str]]:
    words = text.split()
    for i in range(0, len(words), size):
        yield words[i : i + size]


def read_tickets(lines: Iterable[str]) -> Iterator[str]:
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            yield line.lower()


@contextmanager
def timer() -> Iterator[dict[str, float]]:
    result: dict[str, float] = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed"] = time.perf_counter() - start


if __name__ == "__main__":
    assert list(islice(fibonacci(), 10)) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

    assert list(chunk_words("a b c d e", 2)) == [["a", "b"], ["c", "d"], ["e"]]
    assert list(chunk_words("", 3)) == []

    raw = ["  Login BROKEN ", "", "# internal note", "Refund please\n", "   "]
    assert list(read_tickets(raw)) == ["login broken", "refund please"]
    gen = read_tickets(raw)
    assert iter(gen) is gen

    with timer() as t:
        sum(range(10_000))
    assert t["elapsed"] >= 0

    t2: dict[str, float] = {}
    try:
        with timer() as t2:
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert "elapsed" in t2

    print("All ch 07 exercises passed")
