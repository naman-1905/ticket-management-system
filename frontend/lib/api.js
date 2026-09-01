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

function parseError(data, status) {
  if (data?.error?.code) {
    return new ApiError(data.error.code, data.error.message || "Request failed", status, data.error.details);
  }
  if (data?.detail) {
    if (typeof data.detail === "object" && data.detail.code) {
      return new ApiError(data.detail.code, data.detail.message || "Request failed", status, data.detail.details);
    }
    return new ApiError("HTTP_ERROR", String(data.detail), status, {});
  }
  return new ApiError("UNKNOWN", "Something went wrong", status, {});
}

function toQueryString(params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  ).toString();
  return qs ? `?${qs}` : "";
}

async function request(path, { method = "GET", body, headers = {}, auth = true, retry = true } = {}) {
  const finalHeaders = { ...headers };
  if (!(body instanceof FormData)) {
    finalHeaders["Content-Type"] = "application/json";
  }
  if (auth) {
    const token = getAccessToken();
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: finalHeaders,
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
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
    throw parseError(data, res.status);
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
  listAgents: () => request("/users/agents"),
  updateUserRole: (userId, role) => request(`/users/${userId}/role`, { method: "PATCH", body: { role } }),

  listTickets: (params = {}) => request(`/tickets${toQueryString(params)}`),
  searchTickets: (q, params = {}) => request(`/search/tickets${toQueryString({ q, ...params })}`),
  getTicket: (id) => request(`/tickets/${id}`),
  createTicket: (payload, idempotencyKey) =>
    request("/tickets", {
      method: "POST",
      body: payload,
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
    }),
  transitionTicket: (id, to_status, version) =>
    request(`/tickets/${id}/transitions`, { method: "POST", body: { to_status, version } }),
  updateTicketStatus: (id, status) => request(`/tickets/${id}/status`, { method: "PATCH", body: { status } }),
  assignTicket: (id, payload) => request(`/tickets/${id}/assign`, { method: "POST", body: payload }),
  bulkTickets: (payload) => request("/tickets/bulk", { method: "POST", body: payload }),

  listComments: (ticketId) => request(`/tickets/${ticketId}/comments`),
  addComment: (ticketId, payload) => request(`/tickets/${ticketId}/comments`, { method: "POST", body: payload }),

  getTicketSla: (ticketId) => request(`/tickets/${ticketId}/sla`),

  listSlaPolicies: () => request("/sla/policies"),
  createSlaPolicy: (payload) => request("/sla/policies", { method: "POST", body: payload }),
  updateSlaPolicy: (id, payload) => request(`/sla/policies/${id}`, { method: "PATCH", body: payload }),

  listAuditLogs: (params = {}) => request(`/audit/logs${toQueryString(params)}`),

  listOrganizations: () => request("/organizations"),
  createOrganization: (payload) => request("/organizations", { method: "POST", body: payload }),

  listContacts: () => request("/contacts"),
  createContact: (payload) => request("/contacts", { method: "POST", body: payload }),

  listTeams: () => request("/teams"),
  createTeam: (payload) => request("/teams", { method: "POST", body: payload }),
  listQueues: () => request("/queues"),
  createQueue: (payload) => request("/queues", { method: "POST", body: payload }),

  listNotifications: () => request("/notifications"),
  markNotificationsRead: () => request("/notifications/read-all", { method: "POST" }),

  reportSummary: () => request("/reports/tickets/summary"),

  listKBArticles: () => request("/kb/articles"),
  createKBArticle: (payload) => request("/kb/articles", { method: "POST", body: payload }),

  submitCSAT: (ticketId, payload) => request(`/csat/tickets/${ticketId}`, { method: "POST", body: payload }),

  listAttachments: (ticketId) => request(`/attachments/tickets/${ticketId}`),
  uploadAttachment: (ticketId, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/attachments/tickets/${ticketId}`, { method: "POST", body: form });
  },

  listSavedViews: () => request("/saved-views"),
  createSavedView: (payload) => request("/saved-views", { method: "POST", body: payload }),
  listMacros: () => request("/macros"),
  listTags: () => request("/tags"),
};

export { setTokens, clearTokens, getAccessToken };
