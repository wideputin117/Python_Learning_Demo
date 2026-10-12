"""Chapter 08 exercises: decorators.

Run: uv run python exercises/ch08_decorators.py
Replace each `raise NotImplementedError` with your code until all asserts pass.
"""

import functools  # noqa: F401  (you'll need functools.wraps)

VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


def call_counter(func):
    """Wrap `func` so that `wrapped.calls` counts how many times it was called."""
    raise NotImplementedError


def retry(times: int):
    """Decorator factory: retry `func` on any exception, re-raise after `times` failed attempts."""
    raise NotImplementedError


def validate_priority(func):
    """Raise ValueError unless the first positional argument is a valid priority."""
    raise NotImplementedError


if __name__ == "__main__":

    @call_counter
    def greet(name: str) -> str:
        """Say hello."""
        return f"hello {name}"

    assert greet("ana") == "hello ana"
    greet("bo")
    assert greet.calls == 2
    assert greet.__name__ == "greet", "use functools.wraps"
    assert greet.__doc__ == "Say hello."

    attempts = {"n": 0}

    @retry(times=3)
    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("overloaded")
        return "ok"

    assert flaky() == "ok"
    assert attempts["n"] == 3

    @retry(times=2)
    def always_fails() -> None:
        raise TimeoutError("nope")

    try:
        always_fails()
        raise AssertionError("should have raised")
    except TimeoutError:
        pass

    @validate_priority
    def set_priority(priority: str, ticket_id: int) -> str:
        return f"#{ticket_id} -> {priority}"

    assert set_priority("high", 7) == "#7 -> high"
    try:
        set_priority("whenever", 7)
        raise AssertionError("should have raised")
    except ValueError:
        pass
    assert set_priority.__name__ == "set_priority"

    print("All ch 08 exercises passed")
