# SIFT.AI — 3-Developer Delivery Plan

**One frontend engineer, two backend engineers — building on the existing codebase.**

> This plan turns the strategy in [SIFTAI_Product_Compliance_Monetization_Plan.md](SIFTAI_Product_Compliance_Monetization_Plan.md)
> into concrete, assigned engineering work. It is an **extension of the current working project**, not a
> rewrite — every task below names the real files and services it touches. It expands and supersedes the
> earlier [SIFTAI_3_Track_Implementation_Plan.md](SIFTAI_3_Track_Implementation_Plan.md) (which covered only
> Phases 1–2) by carrying the same three roles through the full Phase 1 → Phase 4 roadmap.

**Document version:** 1.0.0 · **Last updated:** 2026-08-11

---

## 0. Where the code actually is today (read this first)

So nobody plans against an imaginary architecture, here is the ground truth of the current build.

**Backend — FastAPI (`backend/app/`)**
- Routes: `health.py`, `documents.py` (upload / list / delete / serve PDF), `chat.py` (SSE streaming),
  `chats.py` (session + message-history CRUD), `audio.py` (transcription).
- Services: `vector_store.py` (Ahnlich), `storage.py` (Cloudflare R2), `web_search.py` (Exa),
  `llm_synthesis.py` (Strict/Enhanced prompts + Gemini synthesis), `agent_router.py` (routing + conflict
  hooks), `cache.py`.
- Data: `db/models.py` currently holds **only `DocumentRecord`**. Chat sessions/messages live in
  `db/chat_registry.py`; documents in `db/registry.py`. Both fall back to in-memory when `DATABASE_URL` is
  unset. **There is no `chambers`, `matters`, `user_profile`, `subscription`, or `audit_log` model yet.**
- Auth: Clerk JWT verification in `auth.py`. Every route except `/health` requires a Bearer token.
- Tests: ~13 suites under `backend/tests/` — the bar is "all green" before merge.

**Frontend — React 19 + Vite + Zustand + Tailwind v4 + Clerk (`frontend/`)**
- Single route: `App.jsx` → `/` renders `Pages/Chat.jsx`. No matter/workspace navigation yet.
- Stores (`frontend/store/`): `auth`, `chat`, `citation`, `documents`, `settings`, `theme`, `upload`, `voice`.
- Components (`frontend/src/components/`): `auth/`, `chat/` (incl. `CitationDrawer`, `CitationCard`,
  `MessageBubble`), `composer/` (`ModeSwitcher`, `UploadButton`, …), `documents/`, `layout/` (`Sidebar`,
  `TopBar`, `SidebarFooter`), `ui/`, `upload/`.
- API plumbing: `frontend/src/lib/api.js` (Clerk-token fetch wrapper), `sseClient.js` (SSE reader),
  `authBridge.js`.
- The endpoint/type contract the frontend already relies on is documented in
  [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md) — treat it as the source of truth for
  existing shapes, and update it as new endpoints land.

**What is missing** is not more AI — it is everything that makes this *legal-specific, chambers-shaped,
compliant, and monetizable*. That is what the three of you are building.

---

## 1. Team roles & ownership boundaries

| Role | Owns | Never blocked on |
|---|---|---|
| **FE — Frontend Engineer** | All React UI/UX: onboarding, matter navigation, chambers UI, PDF highlight viewer, conflict banners, export modal, disclaimers, privacy & billing screens. | Can build against the mock contracts in §3 before backend is live. |
| **BE1 — AI & Legal Grounding** | The intelligence: PDF coordinate extraction, citation metadata, Nigerian citation formatting, conflict scoring, SSE lifecycle, audio briefs, audit-event emission, "no-training" guarantee. | Owns `documents.py` extraction, `chat.py`, `llm_synthesis.py`, `agent_router.py`, `audio.py`. |
| **BE2 — Platform, Data, Exports & Money** | The structure: chambers/matters/profile/subscription/audit schemas + migrations, matter & chambers APIs, role-based access, server-side PDF/DOCX/PPTX export, NDPA endpoints, billing + usage metering. | Owns `db/models.py`, new `matters.py`/`chambers.py`/`exports.py`/`privacy.py`/`billing.py` routes, `export_service.py`. |

**Guiding rule:** BE2 owns *rows and access*, BE1 owns *what the model produces and what gets logged*, FE
owns *everything a lawyer sees and clicks*. When a task spans two owners, the API contract in §3 is the seam.

---

## 2. Delivery phases (mapped to the compliance plan)

The compliance plan defines four phases. This plan keeps that phasing and assigns each phase across the three
devs so they can work in parallel within a phase.

| Phase | Theme (from compliance plan §5) | Goal |
|---|---|---|
| **P1** | Close the "why not NotebookLM" gap | Pitch-ready: disclaimers, roles, Nigerian jurisdiction default, PDF export, privacy policy live. |
| **P2** | Chambers, not individuals | Chambers/team accounts, matter-based organization, DOCX export, DPIA on file, NBA field. |
| **P3** | Monetization-ready | Tiered billing, usage metering, audio briefs, PPTX export, audit logging, paid-tier support. |
| **P4** | Moat-building | Data-residency option, deeper NWLR citation tooling, conflict-of-interest awareness. |

---

## 3. Shared data contract (agree on this before writing code)

This is the seam between all three devs. **BE2 authors the schema, BE1 populates the AI-generated fields,
FE consumes it.** Lock these shapes in week 1; changes go through a quick three-way review.

### 3.1 New database tables (BE2, `backend/app/db/models.py` + migrations)

```
user_profiles         one row per Clerk user
  user_id (PK, Clerk sub)   role            nba_number (nullable)
  chambers_id (FK, null)    default_jurisdiction ("NG")   onboarded_at

chambers
  chambers_id (PK)   name   subscription_tier ("FREE"|"STARTER"|"PRO"|"ENTERPRISE")   created_at

chambers_memberships
  id (PK)   chambers_id (FK)   user_id (FK)   role ("PRINCIPAL"|"PARTNER"|"ASSOCIATE"|"TRAINEE")   status

matters
  matter_id (PK)   chambers_id (FK)   created_by_user_id   title   client_name
  practice_area ("LITIGATION"|"CORPORATE"|"PROPERTY"|"ENERGY"|"FAMILY"|"OTHER")
  jurisdiction ("NG" default)   status ("OPEN"|"CLOSED"|"ARCHIVED")   created_at   updated_at

subscriptions
  chambers_id (FK)   tier   status   period_start   period_end   external_ref (Paystack/Stripe id)

usage_events        append-only meter for volume-based billing
  id   chambers_id   user_id   event_type ("QUERY"|"DOC_UPLOAD"|"EXPORT"|"AUDIO_MIN")   quantity   created_at

audit_log           who asked what, when, which docs (compliance + Enterprise tier)
  id   chambers_id   user_id   action   matter_id (null)   detail (jsonb)   created_at
```

Then add a **nullable `matter_id`** foreign key to the existing `DocumentRecord` and to the chat-session
records in `chat_registry.py`. Nullable so existing rows and personal (non-chambers) use keep working.

### 3.2 New / changed API endpoints

| Endpoint | Owner | Notes |
|---|---|---|
| `GET/PUT /api/v1/me/profile` | BE2 | Onboarding data: role, nba_number, default_jurisdiction. |
| `POST/GET /api/v1/chambers`, `POST /api/v1/chambers/{id}/invite`, `GET /api/v1/chambers/{id}/members` | BE2 | Chambers accounts + invite codes + role-based membership. |
| `POST/GET /api/v1/matters`, `GET/DELETE /api/v1/matters/{id}` | BE2 | Matter CRUD; `GET /{id}` returns the matter workspace (docs + chats). |
| `POST /api/v1/chats/{chat_id}/export` `{format, memo_title, options}` | BE2 | Returns binary `.pdf`/`.docx`/`.pptx` with `Content-Disposition`. |
| `POST /api/v1/privacy/delete-my-data`, `GET /api/v1/privacy/policy-statement` | BE2 | NDPA erasure + machine-readable compliance metadata. |
| `GET /api/v1/billing/plan`, `POST /api/v1/billing/checkout`, `POST /api/v1/billing/webhook` | BE2 | Tier + usage summary + Paystack checkout/webhook. |
| `POST /api/v1/matters/{id}/audio-brief` (or extend `audio.py`) | BE1 | Generates a spoken "audio brief" of a matter. |
| Extended: `documents.py` upload, `chat.py` SSE `metadata` event | BE1 | Add `bounding_boxes` + Nigerian citation fields (below). |

### 3.3 Enriched citation payload (BE1 produces, FE renders)

Extends the existing `InternalCitation` in the integration guide:

```jsonc
{
  "document_id": "uuid",
  "document_name": "Lease.pdf",
  "page_number": 4,
  "chunk_id": "…",
  "bounding_boxes": [{ "x0": 72.0, "y0": 140.5, "x1": 520.0, "y1": 210.0 }],  // NEW — for highlight overlay
  "file_url": "/api/v1/documents/{document_id}/file"
}
```

And the conflict alert gains a confidence score:

```jsonc
{ "has_conflict": true, "severity": "HIGH", "confidence_score": 0.86,
  "contract_clause": "…", "legal_precedent": "…", "explanation": "…" }
```

New SSE events on `POST /api/v1/chat/stream`: `event: mode_change` and a structured `event: error`
(`{ code, message, remediation }`).

---

## 4. Frontend Engineer — task board

**Stack note:** you'll need to add `pdfjs-dist` (or `react-pdf`) for the highlight viewer — it is not yet in
`package.json`. Everything else uses libs already installed (framer-motion, lucide, react-markdown, zustand).

### P1 — Pitch-ready
- [ ] **Role-based onboarding modal.** Extend `components/auth/` (new `OnboardingModal.jsx`) shown on first
      sign-in after Clerk. Collect **role** (Principal Partner/SAN, Partner, Associate, NYSC Trainee, Law
      Student), **NBA enrolment number** (optional, "verified" badge later), **default jurisdiction**
      (default `Nigeria`). Persist via `PUT /api/v1/me/profile`. Add a `frontend/store/profile.js` store.
- [ ] **In-product legal disclaimer.** Sticky, tasteful notice in `layout/SidebarFooter.jsx` or a global
      footer: *"SIFT.AI is an AI research assistant and does not provide autonomous legal advice. Lawyers
      remain responsible for verifying all citations."* (NBA-SLP requirement.)
- [ ] **Jurisdiction front-and-center.** Surface the jurisdiction selector in `composer/` and default to
      Nigeria so it never reads as a generic tool.
- [ ] **Export button (PDF first).** Add an export action to `chat/MessageBubble.jsx` / `ChatActions.jsx` +
      new `chat/ExportModal.jsx`. P1 wires the PDF format only; DOCX/PPTX appear in later phases.

### P2 — Chambers & matters
- [ ] **Matter explorer.** Replace flat document/chat lists in `layout/Sidebar.jsx` with a **Matters & Cases**
      tree. New `frontend/store/matters.js`. Selecting a matter scopes documents, chat history, and the
      citation drawer to that matter (pass `matter_id` through existing `chat`/`documents` stores).
- [ ] **Chambers identity + members.** Chambers badge in `layout/TopBar.jsx`; a members drawer showing each
      user's role. Invite flow UI for Principals (`POST /api/v1/chambers/{id}/invite`).
- [ ] **PDF bounding-box viewer.** Extend `chat/CitationDrawer.jsx` / `CitationCard.jsx`: clicking an internal
      citation opens the PDF (`GET /api/v1/documents/{id}/file`), navigates to `page_number`, and draws
      highlight rectangles from `bounding_boxes` on a `pdfjs-dist` canvas overlay.
- [ ] **Legal conflict banner.** In `chat/MessageBubble.jsx`, render a high-visibility card when
      `conflict_alert.has_conflict` — severity badge (HIGH red / MEDIUM amber / LOW blue), collapsible
      contract-clause vs. precedent comparison. Only show when `confidence_score` clears backend threshold.
- [ ] **"Verify before you rely" affordance** on every citation pill (competence signal, not just CYA).

### P3 — Monetization & polish
- [ ] **Billing/pricing screens.** Tier cards (Free / Starter / Pro / Enterprise) matching compliance §2,
      current-plan + usage-meter display (`GET /api/v1/billing/plan`), and Paystack checkout launch.
- [ ] **DOCX + PPTX** added to `ExportModal.jsx` format options; audio-brief trigger + player UI (extend the
      existing `react-text-to-speech` usage and `voice` store).
- [ ] **Privacy self-service.** In a settings screen: "Delete my data" flow (`POST /api/v1/privacy/delete-my-data`,
      with confirm), link to the live policy statement, and the "we never train on your documents" statement.

### P4 — Moat
- [ ] Surface NWLR-formatted citations distinctly; jurisdiction/court badges. Chambers-level conflict-of-interest
      hints (later, low priority).

---

## 5. Backend Engineer 1 (AI & Legal Grounding) — task board

**Deps to confirm/add in `pyproject.toml`:** PyMuPDF (`fitz`) for coordinates (confirm it's present).

### P1
- [ ] **PDF coordinate extraction.** Update `_extract_pdf_pages` in `api/routes/documents.py` so each chunk
      preserves paragraph bounding boxes `[x0, y0, x1, y1]`. Store `bounding_boxes` in chunk metadata (Ahnlich
      + registry).
- [ ] **Citation metadata propagation.** In `api/routes/chat.py`, include `bounding_boxes` + `file_url` in each
      `internal_citation` on the SSE `metadata` event (contract in §3.3). Keep the existing safe
      `.get("document_name", "Document")` guard.
- [ ] **Nigerian citation prompts.** Enhance `STRICT_MODE_SYSTEM_PROMPT` / `ENHANCED_MODE_SYSTEM_PROMPT` in
      `services/llm_synthesis.py` to teach court codes (`[SC]`, `[CA]`, `[FHC]`) and NWLR format
      `[YYYY] Vol NWLR (Pt. XXX) Page`, while preserving the existing memo structure (Executive Summary /
      Detailed Analysis / Legal Conflicts & Risks / Key Takeaways). **Keep literal citation braces escaped
      (`{{document_name}}`)** — this already caused a `KeyError` regression once (see SESSION_SUMMARY).

### P2
- [ ] **Conflict detection with confidence.** In `services/agent_router.py`, extend
      `detect_legal_conflicts(...)` to attach `confidence_score ∈ [0,1]` and suppress low-confidence
      (<0.75) false alarms, so lawyers are only alerted on genuine contradictions (e.g. interest clause vs.
      statutory cap).
- [ ] **SSE lifecycle events.** Emit `event: mode_change` when Strict/Enhanced toggles mid-session, and
      structured `event: error` payloads (`code`, `message`, `remediation`) when web search / synthesis fails.

### P3
- [ ] **Audio brief generation.** Extend `api/routes/audio.py` (or a new endpoint) to synthesize a spoken
      summary of a *matter* (multiple docs/answers), not just read back one message — the NotebookLM
      "audio overview" analog. Meter it as an `AUDIO_MIN` usage event (hand the count to BE2's meter).
- [ ] **Audit-event emission.** At query time in `chat.py`, emit an audit event (user, action, matter_id,
      documents touched) to BE2's `audit_log` writer — the data half of the Enterprise audit trail.
- [ ] **"No training on your data" enforcement.** Confirm and document in code/comments that no client
      document or chat is used for model training/fine-tuning; expose the guarantee via BE2's policy endpoint.

### P4
- [ ] Deeper NWLR / court-rule tooling and citation validation; jurisdiction-aware retrieval tuning.

---

## 6. Backend Engineer 2 (Platform, Data, Exports & Money) — task board

**Deps to add in `pyproject.toml`:** `reportlab` (PDF), `python-docx` (DOCX), `python-pptx` (PPTX), a
migration tool (`alembic`) if not present, and an HTTP client for Paystack (httpx is fine).

### P1
- [ ] **`user_profiles` model + `/api/v1/me/profile` endpoints** (GET/PUT) so FE onboarding has somewhere to
      write role / NBA number / jurisdiction. Extend `db/models.py`; add the read/write path.
- [ ] **Privacy policy statement endpoint.** `GET /api/v1/privacy/policy-statement` returning machine-readable
      NDPA metadata (lawful basis, encryption in transit/at rest, cross-border-transfer disclosure for Vertex,
      no-model-training guarantee). Pairs with the written policy doc the team drafts separately.

### P2
- [ ] **Chambers & matters schema + migrations** (all tables in §3.1). Add nullable `matter_id` to
      `DocumentRecord` and to chat sessions in `chat_registry.py` — nullable so nothing existing breaks.
- [ ] **Matter CRUD** — `POST/GET /api/v1/matters`, `GET /api/v1/matters/{id}` (returns workspace: docs +
      chats scoped to the matter), `DELETE` (cascade archive). Enforce chambers-scoped access via Clerk user →
      membership lookup.
- [ ] **Chambers accounts** — create chambers, invite codes, member list, role-based visibility (Principal
      sees all matters; Associate sees own + shared).
- [ ] **Export engine — PDF + DOCX.** New `services/export_service.py` + `api/routes/exports.py`
      (`POST /api/v1/chats/{chat_id}/export`). PDF via `reportlab` on formal chambers letterhead (header:
      chambers name, matter ref, date, authoring counsel; body: Executive Summary, Question Presented,
      Findings, Table of Authorities). DOCX via `python-docx` with heading styles for redlining. Stream back
      with `Content-Disposition`.
- [ ] **NDPA erasure.** `POST /api/v1/privacy/delete-my-data` — purge user's R2 objects, Ahnlich vectors, and
      Postgres rows (documents, chats, profile). This must be a real, tested path, not a stub.

### P3
- [ ] **Billing + usage metering.** `subscriptions` + `usage_events` tables; `GET /api/v1/billing/plan`
      (tier + usage summary), Paystack checkout + `POST /api/v1/billing/webhook`. Meter QUERY / DOC_UPLOAD /
      EXPORT / AUDIO_MIN. **Tier gating** enforced server-side (e.g. Free = Strict only, no Enhanced web
      search; caps per compliance §2). Per-chambers pricing with usage overage — not per-seat.
- [ ] **PPTX export** via `python-pptx` added to the export engine.
- [ ] **Audit log writer.** Persist the events BE1 emits (`audit_log`); expose a read endpoint for the
      Enterprise tier.

### P4
- [ ] Data-residency option scaffolding for Enterprise (region-pinned storage config); custom retention policy
      per chambers.

---

## 7. Sprint sequence & dependencies

Work the phases in order; within a phase the three tracks run in parallel. Critical ordering:

- **BE2's schema (§3.1) is the long pole.** Land `user_profiles` in P1 and chambers/matters early in P2 so FE
  and BE1 aren't blocked. Until it lands, FE builds against the §3 mock shapes.
- **BE1's `bounding_boxes` must land before FE's PDF highlight viewer** can be more than a stub. Sequence the
  P2 SSE metadata change ahead of the FE viewer work.
- **BE2's export endpoint must land before FE's export modal** does real downloads (FE can build the modal UI
  against a mocked blob first).
- **Billing (P3) depends on the P2 chambers/subscription tables** existing.

| Milestone | FE | BE1 | BE2 |
|---|---|---|---|
| **End of P1** | Onboarding modal, disclaimer, jurisdiction default, PDF export button (mocked) | Bounding-box extraction + citation metadata, Nigerian citation prompts | `user_profiles` + `/me/profile`, policy-statement endpoint |
| **End of P2** | Matter explorer, chambers UI, PDF highlight viewer, conflict banner | Conflict confidence scoring, SSE lifecycle events | Chambers/matters schema + CRUD, PDF+DOCX export, delete-my-data |
| **End of P3** | Billing screens, DOCX/PPTX + audio-brief UI, privacy self-service | Audio briefs, audit emission, no-training guarantee | Billing + metering + tier gating, PPTX, audit-log writer |
| **End of P4** | NWLR citation display, COI hints | Deeper NWLR tooling | Data-residency + retention scaffolding |

---

## 8. Definition of done / joint QA checklist

- [ ] First-time users complete the role/NBA/jurisdiction onboarding; profile persists across sessions.
- [ ] Clicking an internal citation highlights the exact paragraph rectangle on the PDF canvas.
- [ ] Creating a matter cleanly scopes its documents and chats; nothing leaks across matters or chambers.
- [ ] Exporting a chat produces a downloadable, correctly-formatted `.pdf` and `.docx` (and `.pptx` by P3)
      matching a Nigerian chambers memo layout.
- [ ] Conflict banners appear only when `confidence_score ≥ 0.75`; low-confidence noise is suppressed.
- [ ] `POST /api/v1/privacy/delete-my-data` fully purges R2 + Ahnlich + Postgres (verified, not assumed).
- [ ] `GET /api/v1/privacy/policy-statement` returns accurate NDPA metadata and the no-training guarantee.
- [ ] Tier gating is enforced server-side (Free cannot invoke Enhanced web search); usage events are metered.
- [ ] The in-product legal disclaimer is visible and matches NBA-SLP framing.
- [ ] All existing backend test suites stay green; new endpoints ship with tests under `backend/tests/`.
- [ ] [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md) is updated for every new endpoint/shape.

---

## 9. Non-engineering, same-week items (owner: team lead / legal-savvy teammate)

These are called out in the compliance plan and gate the pitch, but are **not** engineering tasks — track
them here so they don't fall through:

- [ ] Written Privacy Policy + Terms of Service, NDPA-reviewed (feeds BE2's policy endpoint).
- [ ] DPIA for the AI pipeline, on file and referenced in pitch material.
- [ ] Incident/breach response plan + NDPC breach-notification template.
- [ ] Confirm & document encryption in transit/at rest (Neon / R2 defaults).

---

*Summary: BE2 gives the product a spine (chambers, matters, money, compliance), BE1 makes what it says
trustworthy and verifiable (coordinates, Nigerian citations, honest conflict flags, audit trail), and FE makes
all of it feel like software built for a Nigerian chambers rather than a chatbot with file upload. Ship the
phases in order, keep the §3 contract stable, and keep every backend suite green.*
