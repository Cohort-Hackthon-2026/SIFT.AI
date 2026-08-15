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
    if (token.startsWith("guest_")) {
      headers["X-Guest-ID"] = token;
    }
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
    // Attach tier-gate detail when backend returns 402 Payment Required
    if (response.status === 402) {
      try {
        const body = typeof payload === "string" && payload ? JSON.parse(payload) : payload;
        err.tierGate = body?.detail || null;
      } catch {
        err.tierGate = null;
      }
    }
    // If the global opener is registered, call it so UI can show the upgrade modal immediately
    try {
      if (err.tierGate && typeof window !== 'undefined' && window.__sift_open_upgrade) {
        window.__sift_open_upgrade(err.tierGate);
      }
    } catch {
      // ignore
    }
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
    if (response.status === 402) {
      try {
        const body = rawText ? JSON.parse(rawText) : null;
        err.tierGate = body?.detail || null;
      } catch {
        err.tierGate = null;
      }
      try {
        if (err.tierGate && typeof window !== 'undefined' && window.__sift_open_upgrade) {
          window.__sift_open_upgrade(err.tierGate);
        }
      } catch {
        // ignore
      }
    }
    throw err;
  }

  if (!response.body) {
    throw new Error("The server returned an empty event stream.");
  }

  return response.body;
}

async function readEventStream(body, handlers = {}) {
  const reader = body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let currentEvent = null;
  let dataLines = [];

  const dispatch = () => {
    if (!currentEvent || dataLines.length === 0) return;

    const rawData = dataLines.join("\n");
    let data = rawData;
    try {
      data = JSON.parse(rawData);
    } catch {
      // ignore
    }

    if (handlers.onEvent) {
      handlers.onEvent(currentEvent, data);
    }

    if (currentEvent === "status" && handlers.onStatus) {
      handlers.onStatus(data);
    } else if (currentEvent === "metadata" && handlers.onMetadata) {
      handlers.onMetadata(data);
    } else if (currentEvent === "message" && handlers.onMessage) {
      handlers.onMessage(data?.delta ?? data);
    } else if (currentEvent === "mode_change" && handlers.onModeChange) {
      handlers.onModeChange(data);
    } else if (currentEvent === "error" && handlers.onError) {
      handlers.onError(data);
    }
  };

  const processLine = (line) => {
    const normalized = line.endsWith("\r") ? line.slice(0, -1) : line;

    if (normalized === "") {
      dispatch();
      currentEvent = null;
      dataLines = [];
    } else if (normalized.startsWith("event:")) {
      currentEvent = normalized.slice(6).trim();
    } else if (normalized.startsWith("data:")) {
      dataLines.push(normalized.slice(5).trimStart());
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    lines.forEach(processLine);

    if (done) break;
  }

  if (buffer) processLine(buffer);
  dispatch();
}

const encodeId = (id) => encodeURIComponent(String(id || ""));

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

  // --- Export endpoints
  exportChat: (chatId, format = "PDF") =>
    request(`/api/v1/chats/${encodeId(chatId)}/export`, {
      method: "POST",
      body: { format: format.toUpperCase() },
      responseType: "blob",
    }),

  // --- Profile endpoints
  getMyProfile: () => request(`/api/v1/me/profile`),
  updateMyProfile: (patch) => request(`/api/v1/me/profile`, { method: "PUT", body: patch }),

  // --- Billing endpoints
  getBillingPlan: () => request(`/api/v1/billing/plan`),
  startCheckout: (body) => request(`/api/v1/billing/checkout`, { method: "POST", body }),
  verifyPayment: (reference, tier = null) =>
    request(`/api/v1/billing/verify/${encodeURIComponent(reference)}`, {
      method: "GET",
    }),


  // --- Chambers / Teams
  createChambers: (name) => request(`/api/v1/chambers`, { method: "POST", body: { name } }),
  listChambers: () => request(`/api/v1/chambers`),
  joinChambers: (invite_code) => request(`/api/v1/chambers/join`, { method: "POST", body: { invite_code } }),
  getChambersDetail: (id) => request(`/api/v1/chambers/${encodeId(id)}`),
  listChambersMembers: (id) => request(`/api/v1/chambers/${encodeId(id)}/members`),
  updateChambersMemberRole: (id, userId, role) => request(`/api/v1/chambers/${encodeId(id)}/members/${encodeId(userId)}`, { method: "PATCH", body: { role } }),
  removeChambersMember: (id, userId) => request(`/api/v1/chambers/${encodeId(id)}/members/${encodeId(userId)}`, { method: "DELETE" }),

  // --- Matters / Cases
  listMatters: () => request(`/api/v1/matters`),
  createMatter: (body) => request(`/api/v1/matters`, { method: "POST", body }),
  getMatter: (id) => request(`/api/v1/matters/${encodeId(id)}`),
  deleteMatter: (id) => request(`/api/v1/matters/${encodeId(id)}`, { method: "DELETE" }),

  // --- Privacy & NDPA
  getPolicyStatement: () => request(`/api/v1/privacy/policy-statement`),
  deleteMyData: () => request(`/api/v1/privacy/delete-my-data`, { method: "POST" }),
};
