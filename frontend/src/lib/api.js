import { getAuthToken } from "./authBridge";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const token = await getAuthToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
    delete headers["content-type"];
  } else if (options.body && !headers["Content-Type"] && !headers["content-type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body: options.body && typeof options.body !== "string" && !(options.body instanceof FormData)
      ? JSON.stringify(options.body)
      : options.body,
  });

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const rawText = await response.text();
  const payload = rawText && isJson ? JSON.parse(rawText) : rawText;

  if (!response.ok) {
    let detail = response.statusText;
    if (payload && typeof payload === "object") {
      detail = payload.detail || payload.message || detail;
    }
    const err = new Error(detail || "Request failed");
    err.status = response.status;
    throw err;
  }

  if (!rawText) {
    return null;
  }

  return payload;
}

async function stream(path, options = {}) {
  const token = await getAuthToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  headers.Accept = "text/event-stream";

  if (options.body && !headers["Content-Type"] && !headers["content-type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body: options.body && typeof options.body !== "string" && !(options.body instanceof FormData)
      ? JSON.stringify(options.body)
      : options.body,
  });

  if (!response.ok) {
    const rawText = await response.text();
    let detail = response.statusText;
    try {
      const payload = rawText ? JSON.parse(rawText) : null;
      detail = payload?.detail || payload?.message || detail;
    } catch {
      // ignore
    }
    const err = new Error(detail || "Request failed");
    err.status = response.status;
    err.detail = detail;
    throw err;
  }

  return response;
}

export const api = {
  uploadDocument: (formData) =>
    request("/api/v1/documents/upload", { method: "POST", body: formData }),

  listDocuments: async () => {
    const response = await request("/api/v1/documents");
    return response?.documents || [];
  },

  deleteDocument: (documentId) =>
    request(`/api/v1/documents/${documentId}`, { method: "DELETE" }),

  transcribeAudio: (formData) =>
    request("/api/v1/audio/transcribe", { method: "POST", body: formData }),

  createChat: (payload) =>
    request("/api/v1/chats", { method: "POST", body: payload }),

  listChats: () => request("/api/v1/chats"),

  getChat: (chatId) => request(`/api/v1/chats/${chatId}`),

  updateChat: (chatId, payload) =>
    request(`/api/v1/chats/${chatId}`, { method: "PATCH", body: payload }),

  deleteChat: (chatId) => request(`/api/v1/chats/${chatId}`, { method: "DELETE" }),

  listChatMessages: (chatId) => request(`/api/v1/chats/${chatId}/messages`),

  streamChat: (payload) =>
    stream("/api/v1/chat/stream", { method: "POST", body: payload }),
};
