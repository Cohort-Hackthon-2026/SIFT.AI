# SIFT.AI — 3-Engineer Technical Implementation Plan (Phases 1 & 2)

**Document Version:** 1.0.0  
**Target Architecture:** Nigerian Legal AI Research Platform (Chambers, Matters & Verified Citations)  
**Assigned Roles:**
1. **Frontend Engineer:** UI/UX, Matter Navigation, Citation Highlighting & Export UI
2. **Backend Engineer 1:** AI Pipeline, Chunk Coordinate Extraction, Grounded Synthesis & Legal Conflict Engine
3. **Backend Engineer 2:** Platform DB (Neon), Chambers/Matters Architecture, Server-Side PDF/DOCX Generation & NDPA Compliance

---

## 🏛️ System Architecture Overview & Team Interfaces

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                      FRONTEND (React)                       │
                    │  - Matter / Client Explorer      - PDF Viewer + Highlights  │
                    │  - Chat Streaming (SSE)          - Legal Memo Export Modal  │
                    └──────────────┬───────────────────────────────┬──────────────┘
                                   │                               │
                      HTTP / SSE   │                               │  Download Binary
                                   ▼                               ▼
┌──────────────────────────────────────────────────┐  ┌──────────────────────────────────────────────────┐
│             BACKEND 1: AI & SEARCH               │  │          BACKEND 2: PLATFORM & EXPORTS           │
│  - PyMuPDF Coordinate Extraction (`BoundingBox`) │  │  - Chambers & Matter Schemas (Postgres/Neon)     │
│  - Grounded Strict/Enhanced LLM Synthesis        │  │  - Server-side PDF/DOCX Memo Builder             │
│  - Citation & Evidence Generation (NWLR Format)  │  │  - Cloudflare R2 Document Store                  │
│  - Legal Conflict Confidence Scoring             │  │  - NDPA Compliance & Data Erasure Flow           │
└──────────────────────────────────────────────────┘  └──────────────────────────────────────────────────┘
```

---

# 🎨 Track 1: Frontend Engineer Implementation Plan

### 🎯 Primary Objectives
Build a professional, law-chambers-ready interface that feels like enterprise legal practice management rather than a generic chatbot.

---

### 1.1 Matter & Workspace Navigation
- [ ] **Matter Selector & Sidebar Grouping**:
  - Replace flat document/chat listing with a **"Matters & Cases"** tree.
  - Users can create a Matter (e.g. `Suit No: FHC/ABJ/CS/120/2026 — Zenith Bank v. Oando Plc`).
  - Selecting a Matter scopes the document list, research history, and evidence drawer to that matter.
- [ ] **Chambers Switching & Member List UI**:
  - Display Chambers identity badge in top navigation (e.g., `Aluko & Oyebode Chambers`).
  - Team members drawer displaying user role (`Principal Partner`, `Senior Associate`, `NYSC Trainee`).

---

### 1.2 Interactive Citation & PDF Bounding-Box Viewer
- [ ] **Citation Deep-Linking & Highlight Overlay**:
  - When clicking an internal citation chip (`[Doc: NDA.pdf, Page: 4]`), open the integrated PDF viewer drawer.
  - Automatically navigate to the cited `page_number`.
  - Use `react-pdf` / `pdfjs-dist` overlay canvas to draw bounding box highlight rectangles over the exact paragraph coordinates received in `bounding_boxes: [{x0, y0, x1, y1}]`.
- [ ] **Legal Conflict Banner**:
  - Render high-priority warning cards for `⚠️ CONFLICT DETECTED` with severity badge (`HIGH`, `MEDIUM`, `LOW`) and collapsible side-by-side comparison of internal contract vs. external law.

---

### 1.3 Legal Memo Export UI
- [ ] **"Export Legal Research Memo" Modal**:
  - Add an **Export Action** button on any assistant research response or full chat thread.
  - Form options:
    - Format: `PDF Memo (.pdf)` or `Editable Redline (.docx)`.
    - Options: Include Executive Summary, Include Verifiable Citations, Add Chambers Letterhead.
  - Calls `POST /api/v1/matters/{matter_id}/exports/memo` and triggers immediate browser file download.

---

### 1.4 Legal Compliance & Onboarding
- [ ] **In-Product Legal Disclaimer**:
  - Sticky, elegant footer notice adhering to NBA-SLP guidelines: *"SIFT.AI is an AI research assistant and does not provide autonomous legal advice. Lawyers remain professionally responsible for verifying all citations."*
- [ ] **Role-Based Onboarding Modal**:
  - On first sign-in (Clerk), prompt for:
    - Professional Role: `Principal Partner / SAN`, `Partner`, `Associate`, `NYSC Trainee`, `Law Student`.
    - NBA Enrolment Number (Optional verification badge).
    - Default Jurisdiction (Default: `Nigeria (Federal & State Law)`).

---

# 🧠 Track 2: Backend Engineer 1 (AI Pipeline & Legal Grounding)

### 🎯 Primary Objectives
Deliver pinpoint factual accuracy, eliminate hallucinations, extract precise PDF coordinate data, and enforce Nigerian legal citation standards.

---

### 2.1 PDF Extraction with Paragraph Bounding Boxes
- [ ] **PyMuPDF Coordinate Extraction**:
  - Update `_extract_pdf_pages` in `app/api/routes/documents.py`:
  - For each extracted text chunk, preserve bounding box coordinates `[x0, y0, x1, y1]` representing the paragraph polygon on the PDF page.
  - Attach `bounding_boxes` to chunk metadata in the vector store and registry.
- [ ] **Metadata Propagation**:
  - Ensure `internal_citations` in `app/api/routes/chat.py` includes:
    ```json
    {
      "document_id": "uuid",
      "document_name": "Agreement.pdf",
      "page_number": 2,
      "bounding_boxes": [{"x0": 72.0, "y0": 140.5, "x1": 520.0, "y1": 210.0}],
      "file_url": "/api/v1/documents/{document_id}/file"
    }
    ```

---

### 2.2 Nigerian Legal Citations & Structured Output
- [ ] **NWLR & Court Rule System Prompts**:
  - Enhance `STRICT_MODE_SYSTEM_PROMPT` and `ENHANCED_MODE_SYSTEM_PROMPT` in `app/services/llm_synthesis.py`:
  - Teach the model Nigerian legal citation standards:
    - Supreme Court of Nigeria (`[SC]`), Court of Appeal (`[CA]`), Federal High Court (`[FHC]`).
    - Standard law report citation formatting: `[YYYY] Vol NWLR (Pt. XXX) Page`.
  - Maintain the clean markdown structure:
    - `### 📌 Executive Summary`
    - `### 📝 Detailed Legal Analysis`
    - `### ⚖️ Legal Conflicts & Risks`
    - `### 💡 Key Takeaways & Recommendations`

---

### 2.3 Legal Conflict Detection with Confidence Scoring
- [ ] **Conflict Scoring Algorithm in `AgentRouterService`**:
  - Update `detect_legal_conflicts(internal_chunks, web_snippets)`:
  - Add confidence scoring (`confidence_score: float [0.0 - 1.0]`).
  - Filter out low-confidence (<0.75) false alarms so lawyers are only alerted when a genuine contradiction exists (e.g. an interest clause violating statutory caps).

---

### 2.4 Streaming Reliability & Mode Transition Events
- [ ] **Explicit SSE Lifecycle Events**:
  - Add `event: mode_change` when toggling between Strict and Enhanced mode.
  - Emit structured `event: error` payloads with actionable user remediation tips if web search fails.

---

# 🏗️ Track 3: Backend Engineer 2 (Platform, Chambers, Exports & NDPA)

### 🎯 Primary Objectives
Build multi-tenant Chambers and Matter data architecture, server-side PDF/DOCX document export engines, and NDPA compliance data lifecycles.

---

### 3.1 Chambers & Matters Data Architecture (Postgres / Neon)
- [ ] **Database Schema Migrations (`app/db/models.py`)**:
  - **`chambers` Table**: `chambers_id`, `name`, `created_at`, `subscription_tier`.
  - **`chambers_memberships` Table**: `id`, `chambers_id`, `user_id`, `role` (`PRINCIPAL`, `ASSOCIATE`, `TRAINEE`).
  - **`matters` Table**:
    - `matter_id` (PK, UUID)
    - `chambers_id` (FK)
    - `created_by_user_id` (FK)
    - `title` (e.g. `Suit No: FHC/L/CS/45/2026`)
    - `client_name`
    - `practice_area` (`LITIGATION`, `CORPORATE`, `PROPERTY`, `ENERGY`)
    - `created_at`, `updated_at`
  - Link `documents` and `chats` with nullable `matter_id`.
- [ ] **Matter CRUD Endpoints**:
  - `POST /api/v1/matters` — Create new client case.
  - `GET /api/v1/matters` — List all matters for user's chambers.
  - `GET /api/v1/matters/{matter_id}` — Get full matter workspace (documents + chats).
  - `DELETE /api/v1/matters/{matter_id}` — Cascade archive/delete.

---

### 3.2 Server-Side Legal Research Memo Export Engine
- [ ] **PDF & DOCX Memo Generators (`app/services/export_service.py`)**:
  - **PDF Export (using `reportlab`)**:
    - Generates professional legal research memo on formal letterhead layout.
    - Header: Chambers Name, Matter Reference, Date, Authoring Counsel.
    - Body: Executive Summary, Question Presented, Legal Findings, Verifiable Table of Authorities.
  - **DOCX Export (using `python-docx`)**:
    - Generates clean, standard editable `.docx` with formal heading styles, allowing partners to redline and edit before client delivery.
- [ ] **Export Endpoint (`app/api/routes/exports.py`)**:
  - `POST /api/v1/chats/{chat_id}/export` with payload `{ format: "pdf" | "docx", memo_title: "..." }`.
  - Streams back binary file attachment with proper `Content-Disposition`.

---

### 3.3 NDPA Compliance & Security Safeguards
- [ ] **"Delete My Data" Right of Erasure Endpoint**:
  - `POST /api/v1/privacy/delete-my-data`:
  - Permanently purges user documents from Cloudflare R2, vectors from Ahnlich/local store, and chat history from Postgres.
- [ ] **Data Processing Statement & Retention Policy**:
  - Endpoint `GET /api/v1/privacy/policy-statement` returning live machine-readable compliance metadata (NDPA lawful basis, encryption standards, no-model-training guarantee).

---

## 🗓️ Team Synchronization & API Contracts

### Week 1 Deliverables (Foundation)
* **Backend 2**: Deploys Matter database migrations and sets up `/api/v1/matters` endpoints.
* **Backend 1**: Adds paragraph bounding box coordinates to PDF extraction and citation metadata.
* **Frontend**: Implements Matter navigation bar and connects Clerk onboarding role modal.

### Week 2 Deliverables (Integration & Polish)
* **Backend 2**: Implements `reportlab` & `python-docx` export generation engines.
* **Backend 1**: Refines Nigerian legal citation prompt rules and conflict detection confidence scoring.
* **Frontend**: Connects PDF bounding box highlight viewer and adds Export Research Memo download button.

---

### 🧪 Joint Quality Assurance Checklist
- [ ] Clicking a citation in the frontend highlights the exact paragraph rectangle on the PDF canvas.
- [ ] Exporting a chat generates a downloadable `.pdf` and `.docx` legal memo matching Nigerian Chambers standards.
- [ ] Creating a Matter cleanly isolates documents and chats per client case.
- [ ] NDPA "Delete My Data" endpoint completely purges R2 and Postgres records.
- [ ] All 113+ automated tests pass with green status.
