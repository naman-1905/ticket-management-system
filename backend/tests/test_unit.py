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
