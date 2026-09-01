"""Ticket lifecycle transitions and helpers."""

PAUSE_STATUSES = {"WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD"}

DEFAULT_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "CUSTOMER": {
        "NEW": {"OPEN", "CANCELLED"},
        "OPEN": {"CANCELLED"},
        "RESOLVED": {"CLOSED"},
    },
    "AGENT": {
        "NEW": {"OPEN", "IN_PROGRESS", "CANCELLED"},
        "OPEN": {"IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD", "RESOLVED"},
        "IN_PROGRESS": {"WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD", "RESOLVED", "CLOSED"},
        "WAITING_FOR_CUSTOMER": {"IN_PROGRESS", "RESOLVED"},
        "WAITING_FOR_INTERNAL": {"IN_PROGRESS", "RESOLVED"},
        "ON_HOLD": {"IN_PROGRESS", "RESOLVED"},
        "RESOLVED": {"CLOSED", "OPEN"},
        "CLOSED": {"OPEN"},
    },
    "ADMIN": {
        "NEW": {"OPEN", "IN_PROGRESS", "CANCELLED"},
        "OPEN": {"IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD", "RESOLVED", "CLOSED", "CANCELLED"},
        "IN_PROGRESS": {"OPEN", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD", "RESOLVED", "CLOSED"},
        "WAITING_FOR_CUSTOMER": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
        "WAITING_FOR_INTERNAL": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
        "ON_HOLD": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
        "RESOLVED": {"OPEN", "CLOSED"},
        "CLOSED": {"OPEN"},
        "CANCELLED": set(),
    },
    "OWNER": {
        "NEW": {"OPEN", "IN_PROGRESS", "CANCELLED"},
        "OPEN": {"IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD", "RESOLVED", "CLOSED", "CANCELLED"},
        "IN_PROGRESS": {"OPEN", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD", "RESOLVED", "CLOSED"},
        "WAITING_FOR_CUSTOMER": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
        "WAITING_FOR_INTERNAL": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
        "ON_HOLD": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
        "RESOLVED": {"OPEN", "CLOSED"},
        "CLOSED": {"OPEN"},
        "CANCELLED": set(),
    },
    "SUPERVISOR": {
        "NEW": {"OPEN", "IN_PROGRESS", "CANCELLED"},
        "OPEN": {"IN_PROGRESS", "WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD", "RESOLVED"},
        "IN_PROGRESS": {"WAITING_FOR_CUSTOMER", "WAITING_FOR_INTERNAL", "ON_HOLD", "RESOLVED", "CLOSED"},
        "WAITING_FOR_CUSTOMER": {"IN_PROGRESS", "RESOLVED"},
        "WAITING_FOR_INTERNAL": {"IN_PROGRESS", "RESOLVED"},
        "ON_HOLD": {"IN_PROGRESS", "RESOLVED"},
        "RESOLVED": {"CLOSED", "OPEN"},
        "CLOSED": {"OPEN"},
    },
}


def get_allowed_transitions(role: str, current_status: str) -> list[str]:
    role_map = DEFAULT_TRANSITIONS.get(role, DEFAULT_TRANSITIONS.get("AGENT", {}))
    return sorted(role_map.get(current_status, set()))


def can_transition(role: str, from_status: str, to_status: str) -> bool:
    return to_status in get_allowed_transitions(role, from_status)
