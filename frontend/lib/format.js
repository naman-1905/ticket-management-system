import { TICKET_CATEGORIES } from "./constants";

export function formatAuditAction(action) {
  if (!action) return "";

  return action
    .split(".")
    .flatMap((part) => part.split("_"))
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function formatEntityType(entityType) {
  if (!entityType) return "";

  return entityType
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

// "WAITING_FOR_CUSTOMER" -> "Waiting For Customer"
export function formatStatus(status) {
  if (!status) return "";

  return status
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

// "feature-request" -> "Feature Request" (falls back to title-casing unknown values)
export function formatCategory(category) {
  if (!category) return "";
  const match = TICKET_CATEGORIES.find((c) => c.value === category);
  if (match) return match.label;
  return category.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}
