"""Chapter 08 solutions: decorators."""

import functools

VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


def call_counter(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)

    wrapper.calls = 0
    return wrapper


def retry(times: int):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise

        return wrapper

    return decorator


def validate_priority(func):
    @functools.wraps(func)
    def wrapper(priority, *args, **kwargs):
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"invalid priority: {priority!r}")
        return func(priority, *args, **kwargs)

    return wrapper


if __name__ == "__main__":

    @call_counter
    def greet(name: str) -> str:
        """Say hello."""
        return f"hello {name}"

    assert greet("ana") == "hello ana"
    greet("bo")
    assert greet.calls == 2
    assert greet.__name__ == "greet"
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
