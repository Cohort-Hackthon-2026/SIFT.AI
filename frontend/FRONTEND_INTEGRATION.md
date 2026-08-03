# Frontend Integration Guide - Wiring Backend Developer 1's Endpoints

This document maps every endpoint Backend Developer 1 built to the exact place
it plugs into the existing frontend, what's missing to make that wiring
possible, and edge cases to handle. It does not cover chat/streaming - that's
Backend Developer 2's endpoint (`POST /api/v1/chat/stream`), described at the
bottom under "What this repo does NOT give you yet."

**Every endpoint below now requires a Clerk session token** - read
`CLERK_AUTH_INTEGRATION.md` (same folder) first and build the sign-in/sign-up
pages described there before wiring anything here, or every request will
return `401`. The `api.js` shown in section 0 below is the plain version for
reference; `CLERK_AUTH_INTEGRATION.md` has the real one that attaches a token.

## 0. Before any endpoint works: two setup gaps

The frontend currently has **zero HTTP calls anywhere** - no `fetch`, no
`axios`, no API client module, no `.env`, no base URL config. Before wiring
any single endpoint, add:

### a) An API client module

Create `frontend/src/lib/api.js`:

```js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON - keep statusText
    }
    throw new Error(detail);
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
```

### b) Environment config

Create `frontend/.env.example` (there isn't one yet):

```
VITE_API_BASE_URL=http://localhost:8000
```

Copy it to `.env` locally. Vite exposes anything prefixed `VITE_` to
`import.meta.env` automatically - no extra config needed.

### c) CORS (already fixed backend-side)

The API now sends `Access-Control-Allow-Origin` for
`http://localhost:5173` and `http://127.0.0.1:5173` by default
(`CORS_ALLOWED_ORIGINS` env var on the backend if you need to add a deployed
frontend origin later). Without this the browser blocks every request
regardless of what you build - it was missing before this pass.

---

## 1. `POST /api/v1/documents/upload`

**Where it plugs in:** `store/upload.js` + `src/components/upload/UploadItem.jsx`
+ `src/components/upload/UploadDrawer.jsx`.

Right now `addFiles` in `store/upload.js` only stores the raw `File` object
locally with `status: "selected"` - it never sends anything anywhere. Wire it
like this:

1. Add an `uploadFile` action to `store/upload.js` that, per file:
   - sets `status: "processing"` via `updateFile`
   - builds a `FormData` with `file` and optionally `document_name`
     (`user_id` is not a field here - see CLERK_AUTH_INTEGRATION.md)
   - calls `api.uploadDocument(formData)` (auth is attached automatically -
     see the auth bridge pattern in `CLERK_AUTH_INTEGRATION.md`, no token
     argument needed here)
   - on success: `updateFile(id, { status: "completed", documentId: response.document_id, pages: response.page_count })`
     and also push the new document into `store/documents.js` (see next
     section) so the document list and upload drawer stay in sync
   - on failure: `updateFile(id, { status: "error", error: err.message })`

2. In `UploadItem.jsx`, the `status === "processing" | "completed"` branches
   already exist in JSX - they're just never triggered because nothing calls
   `uploadFile`. Trigger it from `DropZone`'s `onDrop` (call `uploadFile` for
   each accepted file right after `addFiles`), not from a separate "confirm"
   button - there isn't one in the current design.

3. **Edge case - warnings field.** The upload response now includes a
   `warnings` array (e.g. for scanned PDFs with no extractable text - see
   below). If `warnings.length > 0`, show it inline in `UploadItem` (a small
   amber note under the status badge) rather than a plain "Ready" state -
   the document was saved but will never surface in search results until OCR
   is added, and a lawyer silently getting zero search hits from a document
   they think is indexed is a bad failure mode to leave unexplained.

4. **Edge case - size limit.** The backend now rejects files over 20MB with
   `413`. `DropZone.jsx` already sets `maxSize: 20 * 1024 * 1024` in
   `react-dropzone`, so this should rarely surface, but handle the `413`
   response text anyway (e.g. "File exceeds the 20MB upload limit") instead
   of a generic error - client-side validation can be bypassed and the two
   limits should tell the same story.

5. **Edge case - non-PDF / corrupted PDF.** Returns `400` with a message
   under `detail`. Surface it as the file's error state, not a toast that
   disappears - the user needs to know *which* file in a multi-file batch
   failed.

---

## 2. `GET /api/v1/documents`

**Where it plugs in:** `store/documents.js` (currently an **empty file**) and
`src/components/documents/{DocumentDrawer,DocumentCard,DocumentStats}.jsx`
(all three are **empty stub files** - nothing has been built here yet).

This is the biggest gap on the frontend side relative to what the backend
now provides. Build:

1. **`store/documents.js`** - a Zustand store with:
   - `documents: []`
   - `fetchDocuments()` -> calls `api.listDocuments()`, sets `documents`
     (auth is attached automatically inside `api.js` - see
     `CLERK_AUTH_INTEGRATION.md`'s auth bridge pattern, no token argument
     needed here)
   - `removeDocument(documentId)` -> optimistic local removal, used after a
     successful delete (see next section)
   - Call `fetchDocuments()` once on app mount (in `Chat.jsx` or `App.jsx`
     via `useEffect`) and again after every successful upload, so the
     drawer never goes stale.

2. **`DocumentCard.jsx`** - one document's summary row/card. The API gives
   you exactly the fields the build plan asks for: `document_name`,
   `page_count`, `file_size_bytes`, `uploaded_at`, plus `chunk_count` (a
   good implicit health signal - 0 chunks means "won't show up in search",
   same case as the upload warning above). Reuse `formatSize` from
   `UploadItem.jsx` (pull it into a shared `utils/format.js` - it's
   currently duplicated logic waiting to happen) and format `uploaded_at`
   with `Intl.DateTimeFormat` or similar.

3. **`DocumentDrawer.jsx`** - list of `DocumentCard`s, structurally the same
   pattern as `UploadDrawer.jsx` (fixed overlay, `X` to close, backed by a
   store's `open`/`close` state - add that state to `store/documents.js`
   since there's nowhere else for it). Trigger it from `TopBar.jsx` (e.g. a
   "Documents" button next to `ModeDropdown`/`ThemeToggle` - there's no
   entry point to open it anywhere currently).

4. **`DocumentStats.jsx`** - small summary strip (total documents, total
   pages, maybe "X documents have no extractable text" using the
   `chunk_count === 0` signal). Optional polish, not required for MVP.

5. **Edge case - empty state.** If `documents` is `[]`, show a clear "No
   documents yet - upload one to get started" rather than a blank drawer.

6. **Edge case - user scoping.** `GET /api/v1/documents` no longer takes a
   `user_id` query param at all - it always returns only the authenticated
   user's own documents, scoped server-side from their Clerk token. As long
   as `api.js` is wired to the auth bridge (see
   `CLERK_AUTH_INTEGRATION.md`), scoping is automatic; there's no
   client-side bookkeeping needed here anymore.

---

## 3. `DELETE /api/v1/documents/{document_id}`

**Where it plugs in:** a delete action on `DocumentCard.jsx` (doesn't exist
yet, since the card itself doesn't exist yet - build them together).

1. Add a trash icon (same `IconButton` pattern used in `UploadItem.jsx`)
   that calls `api.deleteDocument(documentId)`.
2. **Always confirm before calling this.** There's no undo - once Ahnlich's
   chunks and the Postgres record are gone, they're gone. A lawyer deleting
   the wrong case file is a much worse failure than one extra click; use a
   simple confirm dialog or a two-step "tap trash, then confirm" pattern
   consistent with how the rest of the UI handles destructive actions
   (there's no existing pattern for this in the codebase yet - this is the
   first destructive action being wired up).
3. On success, call `removeDocument(documentId)` in the store - don't
   silently leave a stale card until the next full refetch.
4. **Edge case - 404.** If the document was already deleted (e.g. from
   another tab, or a double-click race), the API returns `404`. Treat that
   as a success from the UI's perspective (remove the card locally anyway) -
   the end state the user wants ("this document is gone") is already true.
5. **Edge case - in-flight search.** If a chat response is mid-stream citing
   a document that gets deleted concurrently, that's a Backend Developer 2 /
   chat-endpoint concern (their strict-mode retrieval would just return
   fewer/no results for that document on the next query) - nothing extra
   needed frontend-side beyond refetching the document list after delete.

---

## 4. `POST /api/v1/audio/transcribe`

**Where it plugs in:** `src/components/composer/VoiceButton.jsx` and
`src/components/chat/VoiceModal.jsx` (currently an **empty file**), plus
`utils/UseSpeechRecognition.js`.

The build plan is explicit here: *"Fall back to raw audio recorder
(MediaRecorder API) to send .wav payloads to the backend if browser native
speech-to-text is unavailable."* Right now `VoiceButton.jsx` only implements
the Web Speech API path (`useSpeechRecognition`) and returns `null` entirely
if `!supported` - there is **no fallback path at all**. This is a real gap,
not just an empty stub:

1. Build a second hook, e.g. `utils/useAudioRecorder.js`, using
   `MediaRecorder` to record to a `Blob` (`audio/webm` or `audio/wav`
   depending on browser support - `MediaRecorder.isTypeSupported()` first).
2. In `VoiceButton.jsx`, branch on `useSpeechRecognition().supported`:
   - supported -> current behavior (live transcript into the text input)
   - unsupported -> use the recorder hook instead; on stop, build a
     `FormData` with the recorded blob as `file` and call
     `api.transcribeAudio(formData)`; put the returned `text` into the chat
     input via `useChat().setInput`, same as the Web Speech path does today.
3. **`VoiceModal.jsx`** is where the "Processing" state from the build plan
   (Step 3: "Idle, Listening, Processing") belongs for the fallback path
   specifically, since transcription is a real network round-trip (can take
   a few seconds) unlike the instant local Web Speech API. Show a spinner
   state while `transcribeAudio` is in flight; the Web Speech path doesn't
   need this modal since it's synchronous/live.
4. **Edge case - first-call latency.** The Whisper model lazy-loads on the
   *first* transcription request after the backend starts (by design, so
   the API can boot without the model weights present). The very first
   voice note after a fresh deploy will be noticeably slower than
   subsequent ones. Worth a "warming up..." message rather than looking
   like a hang, if you want to be thorough - not required for MVP.
5. **Edge case - transcription failure.** `502` if the model/transcription
   itself fails, `503` if `faster-whisper` isn't installed at all in that
   environment. Both should fall back to "please type your question
   instead" messaging - don't leave the composer stuck waiting.
6. **Edge case - silence/empty audio.** An empty recording still gets sent;
   the endpoint returns `400` for a genuinely empty upload, but a real
   silent recording will transcribe to `""` successfully. Check for an
   empty/whitespace-only `text` in the response and treat it the same as a
   failure (ask the user to try again) rather than submitting a blank query.

---

## What this repo does NOT give you yet (don't wire these against Backend Dev 1)

- **`POST /api/v1/chat/stream`** - the actual chat/SSE endpoint `SendButton.jsx`
  should call is Backend Developer 2's deliverable, not part of this repo's
  `backend/` yet. `SendButton.jsx` currently has no `onClick` at all - leave
  it that way (or wire it to a local echo for demo purposes) until that
  endpoint exists. See `BACKEND_DEV2_HANDOFF.md` for exactly what it will
  return and how citations/streaming will be shaped.
- **`POST /api/v1/search/strict`** exists and is fully working, but the
  frontend should *not* call it directly. Per the build plan, Backend
  Developer 2's chat endpoint calls it internally server-side when
  `mode == "STRICT"`. The frontend only ever talks to `/chat/stream`; it
  gets search results back already merged into the answer + citations.

---

## Two bugs already in the frontend worth fixing while you're in this code

1. **`ModeSwitcher.jsx` sends `"STRICT"`/`"ENHANCED"` (uppercase), but
   `store/settings.js` initializes `mode: "strict"` and its `modes` array
   uses lowercase values (`"strict"`, `"enhanced"`) that `ModeDropdown.jsx`
   actually renders from.** `ModeSwitcher.jsx` isn't currently imported
   anywhere (it's commented out in `ActionBar.jsx`), so this hasn't broken
   anything yet - but if it gets re-enabled as-is, clicking it will set a
   `mode` value that doesn't match any entry in `modes`, and
   `ModeDropdown.jsx`'s `modes.find(...)` will return `undefined` and
   crash on `current.label`. Fix the casing before wiring the chat endpoint
   to `mode`, since that's the value that will get sent in the
   `POST /api/v1/chat/stream` request body.
2. **`SendButton.jsx` has no `onClick` prop or handler at all** - it's a
   fully static button today. This isn't a bug so much as confirmation
   there's genuinely nothing to wire yet on the send path until Backend
   Developer 2 ships `/chat/stream`.

---

## Auth (now implemented backend-side - see CLERK_AUTH_INTEGRATION.md)

The workaround described in earlier drafts of this doc (generate a random
per-browser ID, send it as `user_id`) is obsolete - **the backend no longer
accepts a client-supplied `user_id` at all.** Every endpoint now requires a
valid Clerk session token and derives `user_id` from it server-side; passing
a `user_id` field anywhere in a request body/form/query string is simply
ignored (it doesn't exist in the request schemas anymore).

This means the upload/list/delete/search wiring described earlier in this
doc needs one addition beyond what's shown there: attach a Clerk token to
every request. See `CLERK_AUTH_INTEGRATION.md` in this same folder for the
full setup (installing `@clerk/react`, building sign-in/sign-up pages -
there are none yet - and the updated `api.js` that attaches the token). Do
that setup before wiring the endpoints in this document, since every one of
them will now return `401` without a valid token.
