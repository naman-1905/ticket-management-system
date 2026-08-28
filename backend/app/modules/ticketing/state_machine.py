from app.core.errors import ConflictError, ForbiddenError
TRANSITIONS = {"OPEN": {"IN_PROGRESS", "ON_HOLD"}, "IN_PROGRESS": {"OPEN", "ON_HOLD", "RESOLVED"}, "ON_HOLD": {"OPEN", "IN_PROGRESS"}, "RESOLVED": {"CLOSED", "OPEN"}, "CLOSED": set()}
def validate_transition(old: str, new: str, role: str):
    if new not in TRANSITIONS.get(old, set()): raise ConflictError(f"Cannot transition from {old} to {new}", "TICKET_STATE_INVALID")
    if new == "RESOLVED" and role == "CUSTOMER": raise ForbiddenError("Customers cannot resolve tickets")
    if old == "RESOLVED" and new == "OPEN" and role not in {"AGENT", "ADMIN"}: raise ForbiddenError("Only staff can reopen tickets")
