"""Chapter 05 solutions: errors & exceptions."""

from typing import Any


class TriageDeskError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(TriageDeskError):
    status_code = 404
    code = "not_found"


class TicketNotFoundError(NotFoundError):
    code = "ticket_not_found"

    def __init__(self, ticket_id: int) -> None:
        super().__init__(f"Ticket {ticket_id} not found")
        self.ticket_id = ticket_id


class ValidationError(TriageDeskError):
    status_code = 422
    code = "validation_error"


def get_ticket(store: dict[int, dict[str, Any]], ticket_id: int) -> dict[str, Any]:
    try:
        return store[ticket_id]
    except KeyError as e:
        raise TicketNotFoundError(ticket_id) from e


def parse_priority(value: object) -> int:
    try:
        p = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError) as e:
        raise ValidationError(f"priority must be a number, got {value!r}") from e
    if not 1 <= p <= 4:
        raise ValidationError(f"priority must be 1-4, got {p}")
    return p


def to_error_response(exc: TriageDeskError) -> tuple[int, dict[str, dict[str, str]]]:
    return exc.status_code, {"error": {"code": exc.code, "message": exc.message}}


def safe_parse_priority(value: object, default: int = 2) -> int:
    try:
        return parse_priority(value)
    except ValidationError:
        return default


if __name__ == "__main__":
    assert issubclass(TicketNotFoundError, NotFoundError)
    assert issubclass(NotFoundError, TriageDeskError)
    assert issubclass(ValidationError, TriageDeskError)
    assert TriageDeskError("x").status_code == 500

    store = {1: {"id": 1, "title": "Refund"}}
    assert get_ticket(store, 1)["title"] == "Refund"
    try:
        get_ticket(store, 99)
    except NotFoundError as e:  # catching the parent class works
        assert isinstance(e, TicketNotFoundError)
        assert e.ticket_id == 99
        assert e.status_code == 404
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
            assert e.status_code == 422
        else:
            raise AssertionError(f"expected ValidationError for {bad!r}")
    try:
        parse_priority("high")
    except ValidationError as e:
        assert isinstance(e.__cause__, ValueError), "chain the ValueError with `from`"

    status, body = to_error_response(TicketNotFoundError(7))
    assert status == 404
    assert body == {"error": {"code": "ticket_not_found", "message": "Ticket 7 not found"}}

    assert safe_parse_priority("2") == 2
    assert safe_parse_priority("nope") == 2
    assert safe_parse_priority(9, default=1) == 1

    print("All ch 05 exercises passed")
