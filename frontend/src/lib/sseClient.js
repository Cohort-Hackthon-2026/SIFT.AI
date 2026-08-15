import { getAuthToken } from "./authBridge";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getErrorMessage(rawText, status) {
  try {
    const payload = JSON.parse(rawText);
    if (Array.isArray(payload?.detail)) {
      return payload.detail.map((item) => item?.msg || String(item)).join("; ");
    }
    return payload?.detail || payload?.message || `Stream request failed (${status})`;
  } catch {
    return rawText || `Stream request failed (${status})`;
  }
}

export async function streamChatQuery({
  payload,
  onStatus,
  onMetadata,
  onToken,
  onModeChange,
  onError,
}) {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(token && token.startsWith("guest_") ? { "X-Guest-ID": token } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const rawText = await response.text();
    const error = new Error(getErrorMessage(rawText, response.status));
    error.status = response.status;
    throw error;
  }

  if (!response.body) {
    throw new Error("The server returned an empty event stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let currentEvent = null;
  let dataLines = [];

  const dispatch = () => {
    if (!currentEvent || dataLines.length === 0) return;

    const rawData = dataLines.join("\n");
    let data;
    try {
      data = JSON.parse(rawData);
    } catch (error) {
      throw new Error(`Invalid ${currentEvent} event from chat stream: ${error.message}`, { cause: error });
    }

    if (currentEvent === "status") onStatus?.(data);
    if (currentEvent === "metadata") onMetadata?.(data);
    if (currentEvent === "message") onToken?.(data.delta || "");
    if (currentEvent === "mode_change") onModeChange?.(data);
    if (currentEvent === "error") onError?.(data);
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
