const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(kind, message, extra = {}) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    Object.assign(this, extra);
  }
}

function classifyStatus(status) {
  if (status === 404) return "session";
  if (status === 429) return "rate_limited";
  if (status === 502) return "infra";
  if (status === 400) return "bad_request";
  return "unknown";
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (cause) {
    throw new ApiError("network", "Can't reach the API — is the backend running?", { cause });
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    throw new ApiError(classifyStatus(response.status), body?.detail || "Something went wrong.", {
      status: response.status,
      body,
    });
  }

  return body;
}

// POST /query — a business-logic failure (safety rejection, retries
// exhausted) still comes back as a normal 200 with an `error` field in the
// body, by backend design: it's a different kind of failure from the
// service being down. Callers branch on the shape of `data`, not on a
// thrown error, for that case.
export function runQuery(question, sessionId) {
  return request("/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      session_id: sessionId || undefined,
    }),
  });
}

export function getSchema({ sessionId, refresh = false } = {}) {
  const params = new URLSearchParams();
  if (refresh) params.set("refresh", "true");
  if (sessionId) params.set("session_id", sessionId);
  const qs = params.toString();
  return request(`/schema${qs ? `?${qs}` : ""}`);
}

export function connectDemo(connectionString) {
  return request("/demo/connect", {
    method: "POST",
    body: JSON.stringify({ connection_string: connectionString }),
  });
}

export function disconnectDemo(sessionId) {
  return request(`/demo/connect/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
}

// Classifies a successful (2xx) /query response body into the shape the UI
// renders. The backend's own three response shapes (Section 9 of the API,
// mirrored in routes/query.py + core/correction.py):
//   success:   { sql, rows, attempts }
//   rejected:  { error, sql }                        — not read-only
//   exhausted: { error, last_sql_tried, last_error }  — retries used up
export function classifyQueryResult(data) {
  if ("rows" in data) return { kind: "success", ...data };
  if ("last_sql_tried" in data) return { kind: "exhausted", ...data };
  return { kind: "rejected", ...data };
}
