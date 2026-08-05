# SIFT.AI — Master Frontend Integration Guide

> **Dual-Audience Specification**: Designed for both **Human Software Engineers** and **AI Coding Agents**. This document specifies every endpoint, data schema, authentication bridge, SSE event contract, and component wiring rule for connecting the React / Next.js frontend to the SIFT.AI FastAPI backend.

---

## 1. System Architecture & Component Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Next.js / Vite React Frontend                      │
│                                                                         │
│  [ Document Sidebar ]   [ Mode Switcher ]   [ Chat Thread & Feed ]     │
│  - Drag & Drop PDF      - Strict Mode       - Streaming Token Output    │
│  - Active PDF List      - Enhanced Mode     - Citation Badge Pills      │
│  - PDF Viewer Drawer                        - Conflict Alert Banners    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                    Clerk JWT Bearer Token Headers
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend Services (8000)                    │
│                                                                         │
│  [ Auth Guard ]       [ PDF Processor ]        [ Agentic SSE Router ]   │
│  Clerk Verification   PyMuPDF Chunking         Strict & Enhanced Engine │
└─────────┬──────────────────┬─────────────────────────────┬──────────────┘
          │                  │                             │
          ▼                  ▼                             ▼
┌───────────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────────┐
│ PostgreSQL / Neon │ │ Cloudflare R2│ │ Ahnlich DB  │ │ Exa AI Legal Web │
│ Registries & Chats│ │ PDF Storage  │ │ Vector Store│ │ Live Web Search  │
└───────────────────┘ └──────────────┘ └─────────────┘ └──────────────────┘
```

---

## 2. Base Configuration & Environment Setup

- **Backend Base URL**: Default `http://localhost:8000` (Dev / Docker) or production deployment domain.
- **Frontend Environment File (`frontend/.env`)**:

  ```env
  VITE_API_BASE_URL=http://localhost:8000
  VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
  ```

- **CORS**: Backend allows `http://localhost:5173` and `http://127.0.0.1:5173` by default.
- **Authentication Header**: Every request (except `/health`) requires:
  `Authorization: Bearer <clerk_session_token>`

---

## 3. Data Models & TypeScript Definitions

For AI agents and human developers, use these exact type structures:

```typescript
// --- Document Management ---
export interface DocumentRecord {
  document_id: string;
  user_id: string;
  document_name: string;
  page_count: number;
  chunk_count: number;
  file_size_bytes: number;
  uploaded_at: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  user_id: string;
  document_name: string;
  page_count: number;
  chunk_count: number;
  file_size_bytes: number;
  uploaded_at: string;
}

// --- Chat Sessions & Messages ---
export type QueryMode = "STRICT" | "ENHANCED";

export interface ChatSession {
  chat_id: string;
  user_id: string;
  title: string;
  mode: QueryMode;
  document_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  message_id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  metadata: MessageMetadata;
  created_at: string;
}

export interface InternalCitation {
  document_id: string;
  document_name: string;
  page_number: number;
  chunk_id: string;
}

export interface ExternalCitation {
  title: string;
  url: string;
  domain: string;
}

export interface LegalConflictAlert {
  has_conflict: boolean;
  severity?: "HIGH" | "MEDIUM" | "LOW";
  contract_clause?: string;
  legal_precedent?: string;
  explanation?: string;
}

export interface MessageMetadata {
  mode?: QueryMode;
  internal_citations?: InternalCitation[];
  external_citations?: ExternalCitation[];
  conflict_alert?: LegalConflictAlert | null;
}

// --- SSE Streaming ---
export interface ChatStreamRequest {
  query: string;
  chat_id?: string;
  mode?: QueryMode;
  document_ids?: string[];
  top_k?: number;
  min_score_threshold?: number;
}

export interface SSEStatusEvent {
  step: string;
  progress: number;
}

export interface SSEMetadataEvent {
  mode: QueryMode;
  internal_citations: InternalCitation[];
  external_citations: ExternalCitation[];
  conflict_alert: LegalConflictAlert | null;
}

export interface SSEMessageEvent {
  delta: string;
}
```

---

## 4. API Authentication Bridge (`src/lib/api.js`)

Copy-pasteable HTTP client wrapping `fetch` with automatic Clerk token injection:

```javascript
import { useAuth } from "@clerk/clerk-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Universal fetch wrapper with Clerk JWT Bearer Token injection.
 */
export async function fetchWithAuth(endpoint, options = {}, getToken) {
  const token = getToken ? await getToken() : null;
  const headers = {
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorBody = await response.json();
      errorDetail = errorBody.detail || errorDetail;
    } catch {
      // Non-JSON response
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) return null;

  // Handle raw binary response (e.g. PDF file serving)
  if (options.responseType === "blob") {
    return response.blob();
  }

  return response.json();
}
```

---

## 5. Endpoints Reference & Code Snippets

### 5.1 Document Management & Cloudflare R2 PDF Serving

| Method & Route | Request Format | Response Format | Purpose |
| --- | --- | --- | --- |
| `POST /api/v1/documents/upload` | `FormData`: `file`, `document_name` | `DocumentUploadResponse` | Upload PDF, extract chunks, push to Ahnlich vector DB, save PDF in R2, register in Postgres. |
| `GET /api/v1/documents` | None | `{ documents: DocumentRecord[] }` | Fetch list of active PDFs uploaded by user. |
| `DELETE /api/v1/documents/{doc_id}` | Path param `doc_id` | `{ document_id: string, deleted: boolean }` | Purge document from Ahnlich, R2, and Postgres. |
| `GET /api/v1/documents/{doc_id}/file` | Path param `doc_id` | Binary stream (`application/pdf`) | Returns raw PDF bytes for split-screen PDF viewer. |

#### React Example: Uploading a Document

```javascript
export async function uploadPdf(file, getToken) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_name", file.name);

  return await fetchWithAuth("/api/v1/documents/upload", {
    method: "POST",
    body: formData,
  }, getToken);
}
```

#### React Example: Fetching PDF Binary for Viewer

```javascript
export async function fetchPdfBlob(documentId, getToken) {
  const blob = await fetchWithAuth(`/api/v1/documents/${documentId}/file`, {
    method: "GET",
    responseType: "blob",
  }, getToken);

  return URL.createObjectURL(blob);
}
```

---

### 5.2 Backend Chat Sessions & Message History

Chat sessions and historical threads are persisted in PostgreSQL.

| Method & Route | Request Format | Response Format | Purpose |
| --- | --- | --- | --- |
| `POST /api/v1/chats` | `{ title?, mode?, document_ids? }` | `ChatSession` | Create a new research chat thread. |
| `GET /api/v1/chats` | None | `{ chats: ChatSession[] }` | List all user chat sessions (ordered by `updated_at`). |
| `GET /api/v1/chats/{chat_id}` | Path param `chat_id` | `ChatSession` | Fetch single chat thread metadata. |
| `PATCH /api/v1/chats/{chat_id}` | `{ title?, mode?, document_ids? }` | `ChatSession` | Update thread title or bound document IDs. |
| `DELETE /api/v1/chats/{chat_id}` | Path param `chat_id` | `{ chat_id: string, deleted: boolean }` | Cascade delete chat thread and message history. |
| `GET /api/v1/chats/{chat_id}/messages` | Path param `chat_id` | `{ messages: ChatMessage[] }` | Fetch full chronological message history. |

#### React Example: Creating a Chat & Fetching History

```javascript
// Create chat thread bound to 2 PDFs
const chat = await fetchWithAuth("/api/v1/chats", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    title: "Lease Contract Review",
    mode: "STRICT",
    document_ids: ["doc_1_uuid", "doc_2_uuid"],
  }),
}, getToken);

// Fetch messages for active chat
const history = await fetchWithAuth(`/api/v1/chats/${chat.chat_id}/messages`, {}, getToken);
console.log("Messages:", history.messages);
```

---

### 5.3 Real-Time SSE Agent Chat Stream (`POST /api/v1/chat/stream`)

Streams real-time tokens, status logs, citations, and conflict alerts over Server-Sent Events.

#### Payload Schema

```json
{
  "query": "What is the penalty clause for early termination?",
  "chat_id": "35b103f9-b378-4697-8e54-7bde7d8d24d5",
  "mode": "STRICT",
  "document_ids": ["doc_1_uuid"],
  "top_k": 5,
  "min_score_threshold": 0.5
}
```

> [!IMPORTANT]
> When `chat_id` is included, the backend **automatically persists both the user query and the full assistant response + citation metadata** into PostgreSQL.

#### Production SSE Stream Reader (`src/lib/sseClient.js`)

```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Handles SSE streaming for POST /api/v1/chat/stream
 */
export async function streamChatQuery({
  payload,
  getToken,
  onStatus,
  onMetadata,
  onToken,
  onError,
  onComplete,
}) {
  try {
    const token = getToken ? await getToken() : null;

    const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Stream HTTP Error ${response.status}: ${errText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep partial line for next iteration

      let currentEvent = null;

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.replace("event:", "").trim();
        } else if (trimmed.startsWith("data:") && currentEvent) {
          const dataStr = trimmed.replace("data:", "").trim();
          try {
            const parsed = JSON.parse(dataStr);

            if (currentEvent === "status") {
              if (onStatus) onStatus(parsed);
              if (parsed.step === "Done" && onComplete) onComplete();
            } else if (currentEvent === "metadata") {
              if (onMetadata) onMetadata(parsed);
            } else if (currentEvent === "message") {
              if (onToken) onToken(parsed.delta);
            }
          } catch (e) {
            console.error("Failed to parse SSE event data:", e);
          }
          currentEvent = null;
        }
      }
    }
  } catch (error) {
    if (onError) onError(error);
  }
}
```

---

### 5.4 Audio / Voice Input Transcription (`POST /api/v1/audio/transcribe`)

Used when browser native Web Speech API is unsupported (e.g. Firefox/Safari fallback):

```javascript
export async function transcribeAudioBlob(audioBlob, getToken) {
  const formData = new FormData();
  formData.append("file", audioBlob, "voice_query.wav");

  const data = await fetchWithAuth("/api/v1/audio/transcribe", {
    method: "POST",
    body: formData,
  }, getToken);

  return data.text; // Pass transcribed string into chat stream query
}
```

---

## 6. UI Component & UX Guidelines

### 1. Citation Pill Rendering Rules

- **Internal PDF Citations**: Render blue pill `📄 [Doc: Lease.pdf, Page: 4]`.
  - **Action**: Clicking pill opens `PdfViewerDrawer`, loads `GET /api/v1/documents/{doc_id}/file`, and scrolls to `page_number`.
- **External Web Citations**: Render green/purple pill `🌐 [Web: supremecourt.gov.ng]`.
  - **Action**: Clicking pill opens URL in external tab.

### 2. Legal Conflict Warning Banner

- If `metadata.conflict_alert` has `has_conflict: true`, display a high-visibility warning container above or below assistant message:
  - **Severity Badge**: Red (`HIGH`), Amber (`MEDIUM`), Blue (`LOW`).
  - **Contract Clause**: Highlight what the document stated.
  - **Legal Precedent**: Highlight what recent statute / web precedent overruled.

### 3. Fallback Response Assertion

- If internal vector store returns low similarity chunks under `STRICT` mode, the backend returns:
  `"Information not found in the uploaded documents."`
- Display this clearly without rendering blank citation pills.

---

## 7. Error Handling & Edge Cases Matrix

| HTTP Status | Trigger Cause | Frontend Action |
| --- | --- | --- |
| `401 Unauthorized` | Missing/Expired Clerk JWT | Redirect to Sign-In page (`/sign-in`). |
| `404 Not Found` | Accessing document or chat belonging to another user | Display "Resource not found" (Security isolation). |
| `400 Bad Request` | Empty query or malformed body | Show toast notification "Query cannot be empty". |
| `422 Unprocessable` | Double stringified JSON payload | Ensure body is `JSON.stringify(object)`, NOT `JSON.stringify(string)`. |
| `503 Unavailable` | Storage or Ahnlich unreachable | Display warning banner "Running in degraded vector mode". |
