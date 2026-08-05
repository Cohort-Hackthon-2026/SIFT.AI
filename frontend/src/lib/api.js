import { getAuthToken } from "./authBridge";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function formatApiError(payload, fallback) {
  const detail = payload?.detail ?? payload?.message;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || String(item)).join("; ");
  }
  return typeof detail === "string" ? detail : fallback;
}

async function request(path, options = {}) {
  const token = await getAuthToken();
  const headers = { ...(options.headers || {}) };
  const { responseType, ...fetchOptions } = options;

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
    ...fetchOptions,
    headers,
    body: options.body && typeof options.body !== "string" && !(options.body instanceof FormData)
      ? JSON.stringify(options.body)
      : options.body,
  });

  if (response.ok && responseType === "blob") {
    return response.blob();
  }

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const rawText = await response.text();
  let payload = rawText;
  if (rawText && isJson) {
    try {
      payload = JSON.parse(rawText);
    } catch {
      payload = rawText;
    }
  }

  if (!response.ok) {
    const detail = formatApiError(payload, response.statusText);
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
      detail = formatApiError(payload, detail);
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

async function readEventStream(response, onEvent) {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("The server did not return a readable event stream.");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (frame) => {
    if (!frame.trim()) return;

    let event = "message";
    const dataLines = [];

    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (!dataLines.length) return;

    const rawData = dataLines.join("\n");
    let data = rawData;
    try {
      data = JSON.parse(rawData);
    } catch {
      // SSE data is allowed to be plain text.
    }
    onEvent({ event, data });
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() || "";
    frames.forEach(dispatch);

    if (done) break;
  }

  dispatch(buffer);
}

const encodeId = (value) => encodeURIComponent(value);

export const api = {
  health: () => request("/health"),

  uploadDocument: (formData) =>
    request("/api/v1/documents/upload", { method: "POST", body: formData }),

  listDocuments: async () => {
    const response = await request("/api/v1/documents");
    return response?.documents || [];
  },

  deleteDocument: (documentId) =>
    request(`/api/v1/documents/${encodeId(documentId)}`, { method: "DELETE" }),

  getDocumentFile: (documentId) =>
    request(`/api/v1/documents/${encodeId(documentId)}/file`, { responseType: "blob" }),

  strictSearch: (payload) =>
    request("/api/v1/search/strict", { method: "POST", body: payload }),

  transcribeAudio: (formData, language) => {
    const query = language ? `?language=${encodeURIComponent(language)}` : "";
    return request(`/api/v1/audio/transcribe${query}`, { method: "POST", body: formData });
  },

  createChat: (payload) =>
    request("/api/v1/chats", { method: "POST", body: payload }),

  listChats: () => request("/api/v1/chats"),

  getChat: (chatId) => request(`/api/v1/chats/${encodeId(chatId)}`),

  updateChat: (chatId, payload) =>
    request(`/api/v1/chats/${encodeId(chatId)}`, { method: "PATCH", body: payload }),

  deleteChat: (chatId) => request(`/api/v1/chats/${encodeId(chatId)}`, { method: "DELETE" }),

  listChatMessages: (chatId) => request(`/api/v1/chats/${encodeId(chatId)}/messages`),

  streamChat: (payload) =>
    stream("/api/v1/chat/stream", { method: "POST", body: payload }),

  readEventStream,
};
