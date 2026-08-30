const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getAccessToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function setTokens({ access_token, refresh_token }) {
  localStorage.setItem("access_token", access_token);
  if (refresh_token) localStorage.setItem("refresh_token", refresh_token);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export class ApiError extends Error {
  constructor(code, message, status, details) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

function toQueryString(params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  ).toString();
  return qs ? `?${qs}` : "";
}

async function request(path, { method = "GET", body, headers = {}, auth = true, retry = true } = {}) {
  const finalHeaders = { "Content-Type": "application/json", ...headers };
  if (auth) {
    const token = getAccessToken();
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: finalHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    // no JSON body
  }

  if (!res.ok) {
    if (res.status === 401 && auth && retry && getRefreshToken() && !path.startsWith("/auth/")) {
      const refreshed = await tryRefresh();
      if (refreshed) return request(path, { method, body, headers, auth, retry: false });
    }
    const err = data?.error || {};
    throw new ApiError(err.code || "UNKNOWN", err.message || "Something went wrong", res.status, err.details);
  }

  return data;
}

async function tryRefresh() {
  const refresh_token = getRefreshToken();
  if (!refresh_token) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    setTokens(await res.json());
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export const api = {
  register: (payload) => request("/auth/register", { method: "POST", body: payload, auth: false }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload, auth: false }),
  logout: () => {
    const refresh_token = getRefreshToken();
    return request("/auth/logout", { method: "POST", body: { refresh_token } }).finally(clearTokens);
  },
  me: () => request("/auth/me"),

  listUsers: (role) => request(`/users${toQueryString({ role })}`),
  updateUserRole: (userId, role) => request(`/users/${userId}/role`, { method: "PATCH", body: { role } }),

  listTickets: (params = {}) => request(`/tickets${toQueryString(params)}`),
  getTicket: (id) => request(`/tickets/${id}`),
  createTicket: (payload, idempotencyKey) =>
    request("/tickets", {
      method: "POST",
      body: payload,
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
    }),
  updateTicketStatus: (id, status) => request(`/tickets/${id}/status`, { method: "PATCH", body: { status } }),
  assignTicket: (id, assignee_id) => request(`/tickets/${id}/assign`, { method: "POST", body: { assignee_id } }),

  listComments: (ticketId) => request(`/tickets/${ticketId}/comments`),
  addComment: (ticketId, payload) => request(`/tickets/${ticketId}/comments`, { method: "POST", body: payload }),

  getTicketSla: (ticketId) => request(`/tickets/${ticketId}/sla`),

  listSlaPolicies: () => request("/sla/policies"),
  createSlaPolicy: (payload) => request("/sla/policies", { method: "POST", body: payload }),
  updateSlaPolicy: (id, payload) => request(`/sla/policies/${id}`, { method: "PATCH", body: payload }),

  listAuditLogs: (params = {}) => request(`/audit/logs${toQueryString(params)}`),
};

export { setTokens, clearTokens, getAccessToken };
