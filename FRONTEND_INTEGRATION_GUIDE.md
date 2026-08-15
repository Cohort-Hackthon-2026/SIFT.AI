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

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface InternalCitation {
  document_id: string;
  document_name: string;
  page_number: number;
  chunk_id: string;
  bounding_boxes?: BoundingBox[];  // NEW — for PDF highlight overlay
  file_url?: string;               // NEW — e.g. "/api/v1/documents/{id}/file"
  source?: "pdf" | "image" | "chat_text";  // NEW — source type for rendering
}

export interface ExternalCitation {
  title: string;
  url: string;
  domain: string;
}

export interface LegalConflictAlert {
  has_conflict: boolean;
  severity?: "HIGH" | "MEDIUM" | "LOW";
  confidence_score?: number;        // NEW — 0.0–1.0, only alerts ≥ 0.75 are shown
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
  images?: string[];                // NEW — base64-encoded inline images (max 3, 5MB each)
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

// NEW SSE events:
export interface SSEModeChangeEvent {
  from: QueryMode;
  to: QueryMode;
}

export interface SSEErrorEvent {
  code: "WEB_SEARCH_FAILED" | "LLM_STREAM_FAILED";
  message: string;
  remediation: string;
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
| `POST /api/v1/documents/upload` | `FormData`: `file`, `document_name`, `source_type` (optional, default `"auto"`) | `DocumentUploadResponse` | Upload PDF or image (PNG, JPEG, WebP, TIFF). PDFs: extract text + bounding boxes. Images: extract text via Gemini Vision. Both: chunk, vectorise, save to R2, register in Postgres. |
| `GET /api/v1/documents` | None | `{ documents: DocumentRecord[] }` | Fetch list of active documents uploaded by user. |
| `DELETE /api/v1/documents/{doc_id}` | Path param `doc_id` | `{ document_id: string, deleted: boolean }` | Purge document from Ahnlich, R2, and Postgres. |
| `GET /api/v1/documents/{doc_id}/file` | Path param `doc_id` | Binary stream (`application/pdf` or image MIME) | Returns raw file bytes for viewer. |

#### React Example: Uploading a Document (PDF or Image)

```javascript
export async function uploadDocument(file, getToken) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_name", file.name);
  // source_type defaults to "auto" — backend detects PDF vs image from MIME type.

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

---

# Part II — Platform, Teams, Billing & Compliance (BE2)

> This part covers the **BE2** surface: user profiles, chambers (team accounts), matters (case workspaces), chat export, billing/usage, NDPA privacy, and the audit log. Everything here uses the **same** Clerk Bearer auth and `fetchWithAuth` client from Part I §4, unless a route is explicitly marked **public** or **webhook**.
>
> The single most important new concept for the FE is the **tier gate**: some actions return **HTTP 402 (Payment Required)** with a structured upgrade hint. 402 is distinct from 401 (not signed in) and 403 (signed in, but not allowed). Treat 402 as "route to the upgrade screen", never as an error toast.

## 8. Tiers & Entitlements (read this first)

The effective plan for a user is their **chambers' `subscription_tier`**, or `FREE` if they aren't in a chambers. Billing is **per-chambers, not per-seat**.

| Capability | FREE | STARTER | PRO | ENTERPRISE |
| --- | --- | --- | --- | --- |
| Query mode | Strict only | Strict + Enhanced | Strict + Enhanced | Strict + Enhanced |
| Export formats | PDF | PDF, DOCX | PDF, DOCX, PPTX | PDF, DOCX, PPTX |
| Chambers (teams) | ❌ | ✅ | ✅ | ✅ |
| Audit log | ❌ | ❌ | ✅ | ✅ |
| Data residency | ❌ | ❌ | ❌ | ✅ |
| Max members | 1 | 5 | 25 | Unlimited |
| Monthly QUERY quota | 50 | 500 | 5,000 | Unlimited |
| Monthly DOC_UPLOAD quota | 20 | 200 | 2,000 | Unlimited |
| Monthly EXPORT quota | 5 | 100 | 1,000 | Unlimited |
| Monthly AUDIO_MIN quota | 30 | 300 | 3,000 | Unlimited |

**A quota `limit` of `null` means unlimited.** Prices are Enterprise-quoted (contact sales); self-serve tiers are STARTER (₦15,000/mo) and PRO (₦60,000/mo).

### The 402 upgrade envelope

Every tier-gated 402 returns this exact `detail` shape — build one handler for all of them:

```typescript
export interface UpgradeRequiredDetail {
  message: string;          // human-readable, safe to show
  current_tier: "FREE" | "STARTER" | "PRO" | "ENTERPRISE";
  upgrade_required: "STARTER" | "PRO" | null; // the minimum tier that unblocks the action
}
// FastAPI wraps it: the response body is { detail: UpgradeRequiredDetail }
```

```javascript
// Centralised handler — call this from your fetch wrapper's error branch.
export function handleTierGate(status, body, { openUpgradeModal }) {
  if (status === 402) {
    const d = body.detail;
    openUpgradeModal({ reason: d.message, target: d.upgrade_required, current: d.current_tier });
    return true; // handled
  }
  return false;
}
```

## 9. BE2 TypeScript Definitions

```typescript
// --- Profile (§10) ---
export type LegalRole = "PRINCIPAL" | "PARTNER" | "ASSOCIATE" | "TRAINEE" | "LAW_STUDENT" | "SAN";
export interface Profile {
  user_id: string;
  role: LegalRole;
  nba_number: string | null;
  chambers_id: string | null;
  default_jurisdiction: string;   // e.g. "NG"
  onboarded_at: string;           // ISO
  updated_at: string;             // ISO
}

// --- Chambers (§11) ---
export type MemberRole = "PRINCIPAL" | "PARTNER" | "ASSOCIATE" | "TRAINEE";
export type Tier = "FREE" | "STARTER" | "PRO" | "ENTERPRISE";
export interface Chambers {
  chambers_id: string;
  name: string;
  subscription_tier: Tier;
  invite_code?: string;           // present only for PRINCIPAL/PARTNER
  created_at: string;
  updated_at: string;
}
export interface ChambersWithRole extends Chambers { my_role: MemberRole | null; }
export interface Membership { chambers_id: string; user_id: string; role: MemberRole; joined_at: string; }
export interface ChambersDetail extends Chambers { my_role: MemberRole; members: Membership[]; }

// --- Matters (§12) ---
export type PracticeArea =
  | "LITIGATION" | "CORPORATE" | "PROPERTY" | "ENERGY" | "FAMILY"
  | "CRIMINAL" | "IP" | "TAX" | "EMPLOYMENT" | "OTHER";
export type MatterStatus = "OPEN" | "CLOSED" | "ARCHIVED";
export interface Matter {
  matter_id: string;
  chambers_id: string | null;
  created_by_user_id: string;
  title: string;
  client_name: string | null;
  practice_area: PracticeArea;
  jurisdiction: string;
  status: MatterStatus;
  created_at: string;
  updated_at: string;
}
export interface MatterWorkspace { matter: Matter; documents: DocumentRecord[]; chats: ChatSession[]; }

// --- Billing (§14) ---
export interface QuotaUsage { used: number; limit: number | null; remaining: number | null; }
export interface PlanResponse {
  tier: Tier;
  chambers_id: string | null;
  entitlements: Record<string, unknown>;
  usage: { period_start: string; quotas: Record<"QUERY"|"DOC_UPLOAD"|"EXPORT"|"AUDIO_MIN", QuotaUsage> };
  plans: Record<Tier, { amount_kobo: number | null; currency: string; self_serve: boolean; label: string; blurb: string }>;
}
export interface CheckoutResponse {
  provider: "paystack" | "mock";
  reference: string;
  tier: Tier;
  amount_kobo: number | null;
  currency: string;
  authorization_url: string | null;   // redirect here when provider === "paystack"
  access_code?: string;
}

// --- Audit (§16) ---
export interface AuditEntry {
  id: string; chambers_id: string | null; user_id: string; action: string;
  matter_id: string | null; detail: Record<string, unknown>; created_at: string;
}
```

## 10. User Profile — `/api/v1/me`

The FE should call `GET /api/v1/me/profile` right after sign-in; it **lazily creates** a default profile (role `ASSOCIATE`, jurisdiction `NG`, no chambers) so onboarding always has a row to edit.

| Method & Route | Request | Response | Notes |
| --- | --- | --- | --- |
| `GET /api/v1/me/profile` | — | `Profile` | Lazily creates on first call. |
| `PUT /api/v1/me/profile` | `{ role?, nba_number?, default_jurisdiction? }` | `Profile` | `role` must be a `LegalRole` (else 422). Values are upper-cased server-side. |

> **Do not** set `chambers_id` here — it's read-only on the profile and is managed exclusively through the chambers create/join/leave flows (§11) so it stays consistent with the memberships table.

```javascript
export const getMyProfile = (getToken) => fetchWithAuth("/api/v1/me/profile", {}, getToken);
export const updateMyProfile = (patch, getToken) => fetchWithAuth("/api/v1/me/profile", {
  method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch),
}, getToken);
```

## 11. Chambers (Team Accounts) — `/api/v1/chambers`

Creating a chambers makes the caller its founding **PRINCIPAL** and mints an **invite code**. Others join with that code. Seat count is capped by the chambers' tier (FREE = solo).

| Method & Route | Request | Response | Notes |
| --- | --- | --- | --- |
| `POST /api/v1/chambers` | `{ name }` | `Chambers` (201) | Caller becomes PRINCIPAL; their `profile.chambers_id` is synced. |
| `GET /api/v1/chambers` | — | `{ chambers: ChambersWithRole[] }` | The caller's chambers with their role in each. |
| `POST /api/v1/chambers/join` | `{ invite_code }` | `{ chambers, membership }` | **404** invalid code; **402** if the seat limit is reached (upgrade envelope). |
| `GET /api/v1/chambers/{id}` | — | `ChambersDetail` | **404** if not a member. `invite_code` present only for PRINCIPAL/PARTNER. |
| `GET /api/v1/chambers/{id}/members` | — | `{ members: Membership[] }` | Any member. |
| `PATCH /api/v1/chambers/{id}/members/{userId}` | `{ role }` | `Membership` | **403** unless caller is PRINCIPAL; **422** invalid role; **404** target not a member. |
| `DELETE /api/v1/chambers/{id}/members/{userId}` | — | `{ removed: true }` | A member may remove themselves (leave); only a PRINCIPAL may remove others (**403** otherwise). Clears the removed user's `profile.chambers_id`. |

```javascript
export const createChambers = (name, getToken) => fetchWithAuth("/api/v1/chambers", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }),
}, getToken);

export const joinChambers = (invite_code, getToken) => fetchWithAuth("/api/v1/chambers/join", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ invite_code }),
}, getToken); // catch 402 -> upgrade modal, 404 -> "invalid code" toast
```

## 12. Matters (Case Workspaces) — `/api/v1/matters`

A matter groups documents + research chats under one case. Visibility is role-aware: the creator always sees their own matters; PRINCIPAL/PARTNER see **all** matters in their chambers; ASSOCIATE/TRAINEE see the ones they created. Cross-account access returns **404** (never 403), so a matter's existence isn't leaked.

| Method & Route | Request | Response | Notes |
| --- | --- | --- | --- |
| `POST /api/v1/matters` | `{ title, client_name?, practice_area?, jurisdiction?, chambers_id? }` | `Matter` (201) | `practice_area` must be a `PracticeArea` (**422** otherwise). If `chambers_id` is set, caller must be a member (**403** otherwise). |
| `GET /api/v1/matters` | — | `{ matters: Matter[] }` | Role-aware union, newest first. |
| `GET /api/v1/matters/{id}` | — | `MatterWorkspace` | `{ matter, documents, chats }`. **404** if not visible. `chats` are the caller's own threads only. |
| `PATCH /api/v1/matters/{id}` | `{ title?, client_name?, practice_area?, jurisdiction?, status? }` | `Matter` | **403** unless owner or PRINCIPAL/PARTNER; **422** invalid `practice_area`/`status`. |
| `DELETE /api/v1/matters/{id}` | — | `{ status: "ARCHIVED", matter, archived_documents, archived_chats }` | **Archive, not destroy** — reversible via `PATCH { status: "OPEN" }`. Documents/chats keep their link. |
| `POST /api/v1/matters/{id}/documents` | `{ document_ids: string[] }` | `{ attached: string[], skipped: string[] }` | Only documents **owned by the caller** attach; others are silently `skipped`. |
| `DELETE /api/v1/matters/{id}/documents/{docId}` | — | `{ detached: true }` | **404** if the doc isn't the caller's. |
| `POST /api/v1/matters/{id}/chats` | `{ chat_ids: string[] }` | `{ attached, skipped }` | Same ownership rule as documents. |
| `DELETE /api/v1/matters/{id}/chats/{chatId}` | — | `{ detached: true }` | **404** if the chat isn't the caller's. |

> **How docs/chats get filed under a matter:** either attach existing ones via the endpoints above, or pass `matter_id` when creating a chat (Part I §5.2) / uploading a document. The matter workspace (`GET /api/v1/matters/{id}`) is the join view.

## 13. Chat Export — `POST /api/v1/chats/{chat_id}/export`

Renders a chat transcript (with its citations, and matter/chambers header if filed) to a downloadable file. **This is a tier-gated binary endpoint**, not JSON.

- Body: `{ "format": "PDF" | "DOCX" | "PPTX" }` (defaults to `PDF`).
- Gate: **FREE → PDF**, **STARTER → +DOCX**, **PRO → +PPTX**. A blocked format returns **402** with the upgrade envelope.
- **422** unsupported format string; **404** unknown chat or a chat you don't own.
- Success: `200` with `Content-Type` `application/pdf` / the OOXML mime, and `Content-Disposition: attachment; filename="..."`. Each successful export meters one `EXPORT` usage event.

```javascript
export async function exportChat(chatId, format, getToken) {
  const token = await getToken();
  const res = await fetch(`${API_BASE_URL}/api/v1/chats/${chatId}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ format }),
  });
  if (res.status === 402) { const b = await res.json(); /* -> upgrade modal */ throw { tierGate: b.detail }; }
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);

  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const filename = /filename="(.+?)"/.exec(disposition)?.[1] || `chat.${format.toLowerCase()}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
```

## 14. Billing & Usage — `/api/v1/billing`

| Method & Route | Request | Response | Notes |
| --- | --- | --- | --- |
| `GET /api/v1/billing/plan` | — | `PlanResponse` | Current tier, entitlements, this month's usage vs quota, and the public price list (`plans`). Drive the usage meters + pricing page from this one call. |
| `POST /api/v1/billing/checkout` | `{ tier, chambers_id?, email?, callback_url? }` | `CheckoutResponse` | Start an upgrade. See rules below. |
| `POST /api/v1/billing/webhook` | Paystack event | `{ status }` | **Webhook, not for the FE.** Paystack calls it directly; verified by HMAC-SHA512 signature. |

**Checkout rules (all enforced server-side):**
- `tier` must be `STARTER` or `PRO`. `ENTERPRISE`/`FREE` → **400** (Enterprise is sales-led). Unknown tier → **422**.
- The caller must be the **PRINCIPAL** of the target chambers (**403** otherwise), and a chambers must exist on their profile or be passed as `chambers_id` (**400** if none — "billing is per-chambers").
- If Paystack is configured, `email` is required (**400** otherwise) and the response has `provider: "paystack"` + an `authorization_url` — **redirect the browser there**.
- If Paystack is **not** configured (dev), the response has `provider: "mock"` and `authorization_url: null` — show a "mock upgrade" state; the tier does not change until a webhook fires.

```javascript
export async function startCheckout({ tier, chambers_id, email, callback_url }, getToken) {
  const body = await fetchWithAuth("/api/v1/billing/checkout", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tier, chambers_id, email, callback_url }),
  }, getToken);
  if (body.provider === "paystack" && body.authorization_url) {
    window.location.href = body.authorization_url; // Paystack hosted page
  }
  return body; // provider === "mock" in dev
}
```

> **Upgrade lifecycle:** checkout only *starts* payment. The chambers' tier flips to the paid plan **only when Paystack calls the webhook** with `charge.success`. After returning from the Paystack page, re-fetch `GET /api/v1/billing/plan` to reflect the new tier (poll briefly if needed, since the webhook is async).

## 15. Privacy / NDPA — `/api/v1/privacy`

| Method & Route | Auth | Response | Notes |
| --- | --- | --- | --- |
| `GET /api/v1/privacy/policy-statement` | **Public** (no token) | Data-handling statement | NDPA 2023 alignment; render on onboarding/settings. |
| `POST /api/v1/privacy/delete-my-data` | Bearer | `{ status: "completed", deleted: {...} }` | **Irreversible right-to-erasure.** Purges the caller's documents (vectors + files + rows), chats, matters, memberships, usage events, audit logs, and profile. |

> Gate the erasure button behind an explicit "type DELETE to confirm" dialog. After it returns, sign the user out / send them back to onboarding — their profile is gone (a fresh default one is minted on next `GET /me/profile`).

## 16. Audit Log — `GET /api/v1/audit`

Reads a chambers' compliance trail. Triple-gated: **PRO+** plan (**402** otherwise), caller must be **PRINCIPAL/PARTNER** (**403** otherwise), and it's always scoped to that one chambers.

- Query: `?limit=` (1–500, default 100).
- Response: `{ chambers_id, tier, count, logs: AuditEntry[] }` (newest first).
- **400** if the caller has no chambers.

```javascript
export const getAuditLog = (limit = 100, getToken) =>
  fetchWithAuth(`/api/v1/audit?limit=${limit}`, {}, getToken); // 402 -> upgrade, 403 -> hide the nav item
```

## 17. BE2 Error Semantics (extends §7)

| HTTP Status | BE2 Trigger | Frontend Action |
| --- | --- | --- |
| `402 Payment Required` | Action needs a higher tier (Enhanced mode, DOCX/PPTX export, chambers seat limit, audit log) | Open the upgrade modal using `detail.upgrade_required`. **Never** a red error toast. |
| `403 Forbidden` | Signed in but lacks the role (e.g. associate editing billing, non-principal changing roles) | Inline "you don't have permission" — do **not** redirect to sign-in. |
| `404 Not Found` | Accessing another user's / another chambers' resource (matters, chambers, chats) | "Not found" — this is deliberate isolation, not a bug. |
| `422 Unprocessable` | Invalid enum (`role`, `practice_area`, `status`, export `format`, unknown billing `tier`) | Validate against the enums in §9 before sending. |

---

## 18. What the FE must build to be in sync with BE2

1. **A global 402 interceptor** in the API client that opens an upgrade modal from the envelope in §8 — every gated route depends on it.
2. **Onboarding**: call `GET /me/profile` post-sign-in; let the user set `role` + `nba_number` via `PUT`.
3. **Chambers screen**: create/join, member list with role management (PRINCIPAL-only), invite-code sharing (shown only to PRINCIPAL/PARTNER).
4. **Matter workspace**: list/create matters, the `{matter, documents, chats}` detail view, attach/detach, archive.
5. **Export menu** on a chat: PDF always; DOCX/PPTX shown but gated (402 → upgrade).
6. **Billing/usage page**: render meters + pricing from `GET /billing/plan`; wire the upgrade CTA to `POST /billing/checkout` and redirect to Paystack; re-fetch the plan on return.
7. **Settings → Privacy**: render the public policy statement; a guarded "delete my data" action.
8. **Audit view** (PRO+, leadership only): table from `GET /audit`; hide the nav entry on 402/403.
