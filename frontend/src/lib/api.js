import { getAuthToken } from "./authBridge";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const token = await getAuthToken();
  const headers = { ...options.headers, Authorization: `Bearer ${token}` };

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // non-json
    }
    const err = new Error(detail);
    err.status = response.status;
    throw err;
  }

  return response.status === 204 ? null : response.json();
}

export const api = {
  uploadDocument: (formData) =>
    request("/api/v1/documents/upload", { method: "POST", body: formData }),

  listDocuments: () => request("/api/v1/documents"),

  deleteDocument: (documentId) =>
    request(`/api/v1/documents/${documentId}`, { method: "DELETE" }),

  transcribeAudio: (formData) =>
    request("/api/v1/audio/transcribe", { method: "POST", body: formData }),
};
