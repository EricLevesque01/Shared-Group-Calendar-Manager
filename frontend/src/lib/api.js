/**
 * API client — wraps all backend endpoints with fetch.
 * Base URL: http://localhost:8000/api
 */

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const error = new Error(body.detail || `Request failed: ${res.status}`);
    error.status = res.status;
    error.body = body;
    throw error;
  }
  if (res.status === 204) return null;
  return res.json();
}

/* ── Users ── */
export const getUsers = () => request("/users/");
export const getUser = (id) => request(`/users/${id}`);
export const createUser = (data) =>
  request("/users/", { method: "POST", body: JSON.stringify(data) });
export const updateUser = (id, data) =>
  request(`/users/${id}`, { method: "PATCH", body: JSON.stringify(data) });

/* ── Groups ── */
export const getGroups = () => request("/groups/");
export const getGroup = (id) => request(`/groups/${id}`);
export const createGroup = (data) =>
  request("/groups/", { method: "POST", body: JSON.stringify(data) });
export const addMember = (groupId, data) =>
  request(`/groups/${groupId}/members`, {
    method: "POST",
    body: JSON.stringify(data),
  });
export const removeMember = (groupId, userId) =>
  request(`/groups/${groupId}/members/${userId}`, { method: "DELETE" });

/* ── Events ── */
export const getEvents = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/events/${qs ? `?${qs}` : ""}`);
};
export const getEvent = (id) => request(`/events/${id}`);
export const createEvent = (data) =>
  request("/events/", { method: "POST", body: JSON.stringify(data) });
export const updateEvent = (id, actorUserId, data) =>
  request(`/events/${id}?actor_user_id=${actorUserId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const cancelEvent = (id, data) =>
  request(`/events/${id}/cancel`, {
    method: "POST",
    body: JSON.stringify(data),
  });

/* ── RSVP ── */
export const rsvp = (data) =>
  request("/attendees/rsvp", { method: "POST", body: JSON.stringify(data) });

/* ── Change Requests ── */
export const getChangeRequests = (eventId) =>
  request(`/change-requests/?event_id=${eventId}`);
export const createChangeRequest = (data) =>
  request("/change-requests/", { method: "POST", body: JSON.stringify(data) });
export const approveChangeRequest = (id) =>
  request(`/change-requests/${id}/approve`, { method: "POST" });
export const rejectChangeRequest = (id) =>
  request(`/change-requests/${id}/reject`, { method: "POST" });

/* ── Agent Chat ── */
export const chatWithAgent = (data) =>
  request("/agent/chat", { method: "POST", body: JSON.stringify(data) });
