"""Chapter 05 exercises: errors & exceptions.

Fill in the TODOs, then run:
    uv run python exercises/ch05_errors.py
Solutions: exercises/solutions/ch05_errors.py
"""

from typing import Any


class TriageDeskError(Exception):
    """TODO: base app error. Class attrs status_code=500, code="internal_error".
    __init__(message) must call super().__init__(message) and store self.message."""


class NotFoundError(Exception):
    """TODO: should inherit from TriageDeskError; status_code=404, code="not_found"."""


class TicketNotFoundError(Exception):
    """TODO: inherit from NotFoundError; code="ticket_not_found".
    __init__(ticket_id) -> message "Ticket {id} not found", store self.ticket_id."""


class ValidationError(Exception):
    """TODO: inherit from TriageDeskError; status_code=422, code="validation_error"."""


def get_ticket(store: dict[int, dict[str, Any]], ticket_id: int) -> dict[str, Any]:
    """TODO: return store[ticket_id]; translate KeyError into TicketNotFoundError (use `from`)."""
    raise NotImplementedError


def parse_priority(value: object) -> int:
    """TODO: int(value) in 1..4, else raise ValidationError (chain the ValueError/TypeError)."""
    raise NotImplementedError


def to_error_response(exc: TriageDeskError) -> tuple[int, dict[str, dict[str, str]]]:
    """TODO: -> (exc.status_code, {"error": {"code": exc.code, "message": exc.message}})."""
    raise NotImplementedError


def safe_parse_priority(value: object, default: int = 2) -> int:
    """TODO: parse_priority, but return `default` on ValidationError (EAFP)."""
    raise NotImplementedError


if __name__ == "__main__":
    assert issubclass(TicketNotFoundError, NotFoundError), "TODO 1: build the exception hierarchy"
    assert issubclass(NotFoundError, TriageDeskError)
    assert issubclass(ValidationError, TriageDeskError)
    assert TriageDeskError("x").status_code == 500  # type: ignore[attr-defined]

    store = {1: {"id": 1, "title": "Refund"}}
    assert get_ticket(store, 1)["title"] == "Refund"
    try:
        get_ticket(store, 99)
    except NotFoundError as e:  # catching the parent class works
        assert isinstance(e, TicketNotFoundError)
        assert e.ticket_id == 99  # type: ignore[attr-defined]
        assert e.status_code == 404  # type: ignore[attr-defined]
        assert str(e) == "Ticket 99 not found"
        assert isinstance(e.__cause__, KeyError), "use `raise ... from e`"
    else:
        raise AssertionError("expected TicketNotFoundError")

    assert parse_priority(3) == 3
    assert parse_priority("4") == 4
    for bad in ["high", None, 0, 5]:
        try:
            parse_priority(bad)
        except ValidationError as e:
            assert e.status_code == 422  # type: ignore[attr-defined]
        else:
            raise AssertionError(f"expected ValidationError for {bad!r}")
    try:
        parse_priority("high")
    except ValidationError as e:
        assert isinstance(e.__cause__, ValueError), "chain the ValueError with `from`"

    status, body = to_error_response(TicketNotFoundError(7))  # type: ignore[arg-type,call-arg]
    assert status == 404
    assert body == {"error": {"code": "ticket_not_found", "message": "Ticket 7 not found"}}

    assert safe_parse_priority("2") == 2
    assert safe_parse_priority("nope") == 2
    assert safe_parse_priority(9, default=1) == 1

    print("All ch 05 exercises passed")
