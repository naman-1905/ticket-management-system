export function hasPermission(user, permission) {
  if (!user) return false;
  if (user.is_platform_admin) return true;
  return Array.isArray(user.permissions) && user.permissions.includes(permission);
}

export function isStaff(user) {
  if (!user) return false;
  return user.user_type === "staff" || ["OWNER", "ADMIN", "SUPERVISOR", "AGENT"].includes(user.role);
}

export function isCustomer(user) {
  if (!user) return false;
  return user.user_type === "customer" || ["CUSTOMER", "CUSTOMER_ADMIN"].includes(user.role);
}

export function homeForUser(user) {
  if (!user) return "/login";
  if (isStaff(user)) return "/dashboard";
  return "/portal/tickets";
}
