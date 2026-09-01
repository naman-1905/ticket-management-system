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
