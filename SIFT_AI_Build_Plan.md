# SIFT.AI — Implementation Roadmap & Task List (Frontend & Backend)

**Project Name:** SIFT.AI (Scoped Intelligence Engine for Legal Research)  
**Core Vision:** A scoped-intelligence legal research assistant built on **Ahnlich AI Infrastructure** that solves AI hallucinations, context-switching tax, and legal access gaps by providing verifiable, citation-backed answers under two user-controlled operational modes: **Strict Mode** (Closed World) and **Enhanced Mode** (Open World with Web Synthesis).

---

## 1. System Architecture & Conceptual Flow

```
                              [ User Request ]
                                     │
                        ┌────────────┴────────────┐
                        ▼                         ▼
                  [ Document Upload ]       [ Natural Language Query ]
                        │                         │
                        ▼                         │
            [ PyMuPDF / pdfplumber ]               │
           (Page & Paragraph Chunking)            │
                        │                         │
                        ▼                         │
             [ Ahnlich AI Infrastructure ]         │
             (Embeddings & Vector Store)          │
                        │                         │
                        └────────────┬────────────┘
                                     │
                                     ▼
                          [ FastAPI Mode Router ]
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           │                                                   │
           ▼                                                   ▼
   [ STRICT MODE ]                                     [ ENHANCED MODE ]
  • Closed World                                      • Open World
  • Ahnlich Vector Search Only                        • Ahnlich Vector Search
  • Internal Page/Paragraph Chunks                    • + Tavily/Serper Web Search
           │                                          • Conflict Flagging Engine
           │                                                   │
           └─────────────────────────┬─────────────────────────┘
                                     │
                                     ▼
                           [ LLM Synthesis Engine ]
                         (Claude / GPT-4 Prompted)
                                     │
                                     ▼
                       [ Next.js Chat & Citation UI ]
                     • Internal vs. External Citations
                     • Split-Screen PDF Citation Viewer
                     • Visual Conflict Badges
```

---

## 2. Environment Setup & Prerequisites

### 2.1 Services & Infrastructure Setup
- [ ] **Ahnlich AI Container Deployment**:
  - Deploy `ghcr.io/deven96/ahnlich-ai:latest` via Docker.
  - Expose port `1370` for API communication.
  - Test store initialization using the Ahnlich CLI / SDK.
- [ ] **Third-Party API Provisioning**:
  - Obtain API keys for Anthropic Claude (or OpenAI GPT-4).
  - Obtain API keys for Tavily API or Serper API (web search for AI agents).
- [ ] **Environment Configurations**:
  - Configure `.env` files for both Backend and Frontend projects.

---

## 3. Backend Implementation Steps (Python / FastAPI)

### Step 1: Project Initialization & Ahnlich Client Setup
- [ ] Set up Python 3.11+ project using `Poetry` or `pipenv`.
- [ ] Install core dependencies: `fastapi`, `uvicorn`, `pydantic`, `pymupdf` (PyMuPDF), `httpx`, `python-dotenv`, `ahnlich-client` (or gRPC/HTTP wrapper).
- [ ] Create `app/core/config.py` for environment variables (`AHNLICH_HOST`, `AHNLICH_PORT`, `LLM_API_KEY`, `TAVILY_API_KEY`).
- [ ] Create `app/services/ahnlich_service.py`:
  - Implement store initialization:
    ```sql
    CREATESTORE legal_docs QUERYMODEL all-minilm-16-v2 INDEXMODEL all-minilm-16-v2 PREDICATES (doc_id, file_name, page_number) STOREORIGINAL
    ```
  - Implement vector insertion helper (`SET`) storing text chunks alongside metadata (`doc_id`, `file_name`, `page_number`, `paragraph_number`).
  - Implement similarity query function (`GETSIMN` with predicate filtering).

### Step 2: PDF Ingestion & Intelligent Chunking Pipeline
- [ ] Create `app/services/pdf_processor.py`:
  - Implement PDF file validation (max file size, valid PDF structure).
  - Parse text while preserving structural layout: extract text per page and split into paragraphs.
  - Attach granular metadata to every chunk: `doc_id`, `file_name`, `page_number` (1-indexed), `paragraph_index`, and `char_offsets`.
  - Implement semantic chunking strategy (~300–500 tokens per chunk with 50-token overlap).
- [ ] Connect `pdf_processor` to `ahnlich_service`:
  - Embed and push chunks into Ahnlich `legal_docs` store.
  - Store original PDF files in local storage (`/uploads`) or S3-compatible storage for PDF viewer serving.

### Step 3: Strict Mode RAG Pipeline (Closed World)
- [ ] Create `app/services/rag_service.py`:
  - Implement `query_strict_mode(query_text: str, doc_ids: List[str], top_k: int = 5)`:
    - Execute Ahnlich similarity search: `GETSIMN top_k WITH [query_text] USING cosinesimilarity IN legal_docs WHERE (doc_id IN doc_ids)`.
    - Retrieve top match chunks + metadata (`page_number`, `paragraph_index`).
    - Construct strict grounding system prompt:
      > *"You are SIFT.AI, a legal research assistant operating in Strict Mode. Answer the query using ONLY the provided document chunks. Every claim MUST include an internal citation format: [Document Title, p.X, ¶Y]. If the information is not in the text, explicitly state that it cannot be determined from the provided files."*
    - Send context + prompt to Synthesis LLM (Claude/GPT-4).
    - Parse structured response output with internal citation metadata.

### Step 4: Enhanced Mode & Web Search Router (Open World)
- [ ] Implement Tavily / Serper API Integration in `app/services/web_search.py`:
  - Create web search function `search_external_legal_web(query: str, domain_filter: str = "ng")`.
  - Fetch clean, AI-ready snippets, page titles, and source URLs.
- [ ] Expand `rag_service.py` with `query_enhanced_mode(query_text: str, doc_ids: List[str])`:
  - Step A: Execute internal Ahnlich vector search (as in Strict Mode).
  - Step B: Identify search keyphrases / legal topics and execute Tavily web search.
  - Step C: Assemble hybrid prompt containing both **Internal Context** (with page/paragraph tags) and **External Context** (with URL tags).
  - Step D: Instruct LLM to synthesize answer and identify potential **Legal Conflicts** (e.g., if a clause in an uploaded contract conflicts with recent statutory or appellate changes found on the web).
  - Step E: Format response with distinct citation tags: `[Internal: Doc Name, p.X, ¶Y]` vs `[External: Source Title, URL]`.

### Step 5: FastAPI REST Endpoints & Streaming Response
- [ ] Create API routes in `app/api/v1/`:
  - `POST /api/v1/documents/upload`: Accept multi-part PDF uploads, process & index into Ahnlich. Returns `doc_id`, metadata, and page count.
  - `GET /api/v1/documents`: List uploaded documents with status and metadata.
  - `DELETE /api/v1/documents/{doc_id}`: Remove document chunks from Ahnlich store.
  - `POST /api/v1/query`: Main research query endpoint.
    - **Request Body**: `{ "query": "...", "mode": "strict" | "enhanced", "doc_ids": [...], "stream": true }`.
    - **Response**: Server-Sent Events (SSE) stream for real-time text generation + JSON payload containing parsed citation objects and conflict flags.
  - `GET /api/v1/documents/{doc_id}/file`: Serve PDF binary for client-side rendering.

---

## 4. Frontend Implementation Steps (Next.js / TypeScript / React)

### Step 1: Project Setup & Component Architecture
- [ ] Initialize Next.js 14+ project with TypeScript, Tailwind CSS, and App Router.
- [ ] Install icons & UI helpers: `lucide-react`, `clsx`, `tailwind-merge`, `@radix-ui/react-toggle`, `pdfjs-dist` or `react-pdf`.
- [ ] Define global types in `types/sift.ts`:
  - `DocumentItem`, `ChatMessage`, `Citation` (`InternalCitation` | `ExternalCitation`), `QueryMode` (`'strict' | 'enhanced'`), `ConflictAlert`.

### Step 2: Document Management & Upload Workspace Sidebar
- [ ] Create `components/workspace/DocumentSidebar.tsx`:
  - Document list showing file name, page count, upload date, and active toggle.
  - File Dropzone component supporting drag-and-drop PDF uploads with upload progress indicators.
  - Selection checkboxes for scoping queries to specific documents.

### Step 3: Scoped Intelligence Chat UI & Mode Toggle Switch
- [ ] Create `components/chat/ModeToggleSwitch.tsx`:
  - **The Killer Feature Toggle**: Prominent UI control switching between **Strict Mode** (Shield icon / Amber-Green highlight) and **Enhanced Mode** (Globe icon / Indigo highlight).
  - Tooltip explaining mode impact (*Strict: Document-only closed world* vs *Enhanced: Web-assisted research*).
- [ ] Create `components/chat/ChatContainer.tsx` & `ChatMessage.tsx`:
  - Message thread display with streaming text animation.
  - Mode indicator badge on every assistant response ("Answered in Strict Mode" / "Answered in Enhanced Mode").
  - Formatted query input box with send button and mode indicator.

### Step 4: Citation Rendering & Split-Screen PDF Viewer
- [ ] Create `components/chat/CitationBadge.tsx`:
  - **Internal Citation Badge**: Clickable blue pill showing `📄 [Lease Agreement, p. 4, ¶ 2]`. Clicking triggers the PDF viewer sidebar and jumps directly to page 4.
  - **External Citation Badge**: Distinct green/purple pill showing `🌐 [Court of Appeal, 2025 Ruling]`. Clicking opens modal preview or external tab.
- [ ] Create `components/viewer/PdfViewerDrawer.tsx` (Split-Screen UX):
  - Side-by-side or collapsible drawer rendering the PDF document using `pdfjs-dist`.
  - Programmatic navigation: Jump to page and highlight target text/paragraph upon internal citation click.

### Step 5: Visual Conflict Flagging Component
- [ ] Create `components/chat/ConflictAlertBanner.tsx`:
  - High-visibility banner rendered when Enhanced Mode detects a discrepancy between document text and live legal precedents.
  - Clear visual layout showing **Contract Clause** vs. **Recent Legal Ruling/Statute** side-by-side.

---

## 5. Step-by-Step Sprint Execution Roadmap

| Sprint / Timeline | Focus Area | Detailed Deliverables |
| :--- | :--- | :--- |
| **Weeks 1–2** | **Foundation & Strict Mode** | • Docker deploy Ahnlich AI container.<br>• Build FastAPI PDF parsing & paragraph chunking pipeline.<br>• Ahnlich store creation and embedding generation.<br>• Strict Mode RAG retrieval endpoint.<br>• Next.js layout, PDF upload dropzone, basic chat UI. |
| **Weeks 3–4** | **Enhanced Mode & Mode Router** | • Tavily / Serper API web search integration.<br>• Mode Router logic (Strict vs. Enhanced execution path).<br>• Hybrid prompt synthesis for LLM.<br>• Internal vs. External citation data structures.<br>• Next.js Mode Toggle Switch & split-screen PDF Citation Viewer. |
| **Weeks 5–6** | **Conflict Flagging & Demo Polish** | • Implement LLM legal conflict detection & alert UI.<br>• Visual polish: custom citation badges, smooth PDF jumping.<br>• Performance optimization (caching Ahnlich responses, streaming SSE).<br>• End-to-end testing with real Nigerian legal documents & contracts.<br>• Demo Day script rehearsal. |

---

## 6. Actionable Developer Checklist

### Backend Developer Checklist
- [ ] `POST /api/v1/documents/upload` - PDF parsing, paragraph metadata tagging, Ahnlich vector push.
- [ ] `GETSIMN` query wrapper in Python interacting with Ahnlich AI service on port 1370.
- [ ] Strict Mode LLM prompt construction with mandatory internal citation constraints.
- [ ] Enhanced Mode Tavily API web search client and result parsing.
- [ ] Conflict detection logic comparing vector context against web search results.
- [ ] Server-Sent Events (SSE) streaming handler for chat queries.

### Frontend Developer Checklist
- [ ] Next.js 14 App Router project setup with Tailwind CSS and Radix UI.
- [ ] Drag-and-drop PDF upload component with status updates.
- [ ] Strict / Enhanced Mode toggle switch with active state synchronization.
- [ ] Chat message feed supporting real-time streaming output.
- [ ] Citation pill components (`InternalCitation` vs `ExternalCitation`).
- [ ] Split-screen PDF viewer with deep-linking to page and paragraph numbers.
- [ ] Conflict alert banner UI component.
