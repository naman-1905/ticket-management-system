// Single source of truth for enum values shared with the backend.
// Keep in sync with backend/app/models.py, core/permissions.py and domain/ticket_lifecycle.py.

export const TICKET_STATUSES = [
  "NEW",
  "OPEN",
  "IN_PROGRESS",
  "WAITING_FOR_CUSTOMER",
  "WAITING_FOR_INTERNAL",
  "ON_HOLD",
  "RESOLVED",
  "CLOSED",
  "CANCELLED",
];

export const TICKET_PRIORITIES = ["P1", "P2", "P3", "P4"];

// Values must match backend role names exactly (see core/permissions.py).
export const ROLES = [
  "CUSTOMER",
  "CUSTOMER_ADMIN",
  "AGENT",
  "SUPERVISOR",
  "ADMIN",
  "OWNER",
];