from app.domain.ticket_lifecycle import can_transition, get_allowed_transitions, PAUSE_STATUSES


def test_agent_can_open_new_ticket():
    assert can_transition("AGENT", "NEW", "OPEN")
    assert "OPEN" in get_allowed_transitions("AGENT", "NEW")


def test_customer_cannot_assign_in_progress():
    assert not can_transition("CUSTOMER", "NEW", "IN_PROGRESS")


def test_pause_statuses():
    assert "WAITING_FOR_CUSTOMER" in PAUSE_STATUSES


def test_error_helper():
    from app.core.errors import raise_api_error
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        raise_api_error(404, "NOT_FOUND", "missing")
    assert exc.value.detail["code"] == "NOT_FOUND"


def test_owner_cannot_leave_cancelled():
    assert get_allowed_transitions("OWNER", "CANCELLED") == []
    assert not can_transition("OWNER", "CANCELLED", "OPEN")


def test_customer_cannot_resolve_but_can_close():
    assert not can_transition("CUSTOMER", "NEW", "RESOLVED")
    assert can_transition("CUSTOMER", "NEW", "OPEN")
    assert can_transition("CUSTOMER", "RESOLVED", "CLOSED")
    assert not can_transition("CUSTOMER", "RESOLVED", "IN_PROGRESS")


def test_reopen_from_closed():
    for role in ("OWNER", "ADMIN", "AGENT"):
        assert can_transition(role, "CLOSED", "OPEN")
        assert not can_transition(role, "CLOSED", "RESOLVED")


def test_unknown_role_falls_back_to_agent():
    assert get_allowed_transitions("GHOST_ROLE", "OPEN") == get_allowed_transitions("AGENT", "OPEN")


def test_pause_statuses_are_non_terminal_only():
    assert PAUSE_STATUSES == {"WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD"}
    for s in ("RESOLVED", "CLOSED", "CANCELLED"):
        assert s not in PAUSE_STATUSES


def test_allowed_transitions_sorted_and_unique():
    allowed = get_allowed_transitions("OWNER", "OPEN")
    assert allowed == sorted(allowed)
    assert len(allowed) == len(set(allowed))


def test_csat_score_bounds():
    import pytest
    from pydantic import ValidationError
    from app.schemas import CSATIn

    assert CSATIn(score=1).score == 1
    assert CSATIn(score=5).score == 5
    with pytest.raises(ValidationError):
        CSATIn(score=0)
    with pytest.raises(ValidationError):
        CSATIn(score=6)


def test_ticket_create_priority_pattern():
    import pytest
    from pydantic import ValidationError
    from app.schemas import TicketCreate

    assert TicketCreate(title="t", description="d").priority == "P3"
    with pytest.raises(ValidationError):
        TicketCreate(title="t", description="d", priority="P9")


def test_build_search_vector():
    from app.services.tickets import build_search_vector

    class T:
        ticket_number = "TCK-000001"
        title = "Hello World"
        description = "Some Desc"

    assert build_search_vector(T()) == "tck-000001 hello world some desc"


def test_event_types_registered():
    from app.domain.events import EVENT_TYPES, is_known_event_type

    assert "ticket.created" in EVENT_TYPES
    assert "ticket.status_changed" in EVENT_TYPES
    assert is_known_event_type("ticket.created")
    assert is_known_event_type("ticket.status_changed")
    assert not is_known_event_type("does.not.exist")


def test_missing_payload_keys():
    from app.domain.events import missing_payload_keys

    # ticket.created requires ticket_id + ticket_number.
    assert missing_payload_keys("ticket.created", {"ticket_number": "TCK-1"}) == ["ticket_id"]
    assert missing_payload_keys("ticket.created", {"ticket_id": "x", "ticket_number": "y"}) == []

    # ticket.status_changed requires from_status + to_status (and ticket_id).
    missing = missing_payload_keys("ticket.status_changed", {"ticket_id": "x"})
    assert "from_status" in missing and "to_status" in missing
    assert missing_payload_keys(
        "ticket.status_changed",
        {"ticket_id": "x", "from_status": "NEW", "to_status": "OPEN"},
    ) == []

    # Unknown event type -> no keys enforced.
    assert missing_payload_keys("unknown.type", {}) == []


def test_register_builtin_consumers_is_idempotent():
    from app.services import events as ev
    from app.services.event_consumers import register_builtin_consumers

    register_builtin_consumers()
    first = [name for name, _ in ev.CONSUMERS.get("ticket.status_changed", [])]
    register_builtin_consumers()
    second = [name for name, _ in ev.CONSUMERS.get("ticket.status_changed", [])]
    assert "ticket_status_notify" in first
    assert first == second  # re-registration must not duplicate consumers

