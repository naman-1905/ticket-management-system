"""Versioned domain-event registry (Track O).

Every domain event type has a ``schema_version`` and a documented set of required
payload keys. Producers call :func:`app.services.events.emit_event` which validates
the type is registered and the payload carries its required keys, so a malformed
event fails fast at the producer instead of being discovered by a consumer.

Consumers may branch on ``(event_type, schema_version)`` to keep working across
payload versions during rollout. Adding a new event type here (and its required
keys below) is the single step needed to make it emit-able and relay-able.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EventType:
    name: str
    schema_version: int
    description: str


EVENT_TYPES: dict[str, EventType] = {
    "ticket.created": EventType("ticket.created", 1, "A ticket was created."),
    "ticket.status_changed": EventType(
        "ticket.status_changed", 1, "A ticket changed status (from -> to)."
    ),
    "ticket.updated": EventType(
        "ticket.updated", 1, "A ticket's metadata (title/priority/category/project/deadline) changed."
    ),
}

# Required payload keys per event type. emit_event() rejects a payload that is
# missing any of these, so consumers can rely on the documented shape.
REQUIRED_PAYLOAD_KEYS: dict[str, tuple[str, ...]] = {
    "ticket.created": ("ticket_id", "ticket_number"),
    "ticket.status_changed": ("ticket_id", "from_status", "to_status"),
    "ticket.updated": ("ticket_id",),
}


def get_event_type(name: str) -> EventType | None:
    """Return the registered EventType for ``name`` or None if unregistered."""
    return EVENT_TYPES.get(name)


def is_known_event_type(name: str) -> bool:
    return name in EVENT_TYPES


def missing_payload_keys(event_type: str, payload: dict | None) -> list[str]:
    """Return the required payload keys absent from ``payload`` (empty if complete)."""
    required = REQUIRED_PAYLOAD_KEYS.get(event_type, ())
    payload = payload or {}
    return [key for key in required if key not in payload]
