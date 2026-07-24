Here is the raw Markdown file.

I have restored the backend stack back to **Python / FastAPI** as originally specified in your initial blueprint (while keeping the frontend strictly on **React / Vite**), updated all developer tasks and checklists accordingly, and expanded the ASCII flowchart to accurately detail every step of the pipeline.

```markdown
# 📋 SIFT.AI — Complete Implementation Roadmap & Comprehensive Task Breakdown

**Project Name:** SIFT.AI (Scoped Intelligence Engine for Legal & Medical Research)[cite: 1] 
**Core Vision:** A precision-controlled research assistant powered by **Ahnlich AI Infrastructure**[cite: 1] that eliminates hallucinations and context-switching taxes by offering two distinct operational modes: **Strict Mode** (Closed World / 100% PDF Evidence) and **Enhanced Mode** (Open World / Web Synthesis + Conflict Flagging Engine)[cite: 1].

---

## 1. System Architecture & Conceptual Flow


```

```
                           ┌─────────────────────────────────────────────────────────┐
                           │             React (Vite) Frontend Client                │
                           │  • Drag-and-Drop Multi-PDF Upload Panel                 │
                           │  • Multi-Modal Query Bar (Text + Web Speech STT)         │
                           │  • Strict / Enhanced Mode Switcher Control              │
                           │  • Interactive Split-Screen Evidence Drawer & TTS       │
                           └────────────────────────────┬────────────────────────────┘
                                                        │
                                                        ▼
                           ┌─────────────────────────────────────────────────────────┐
                           │              FastAPI Backend Query Router               │
                           │              `POST /api/v1/chat/stream`                 │
                           └──────────────┬───────────────────────────┬──────────────┘
                                          │                           │
                           ┌──────────────┴──────────────┐            │
                           ▼                             │            │
         ┌─────────────────────────────────┐             │            │
         │   Backend Dev 1 Ingestion       │             │            │
         │ • PyMuPDF Structural Extraction │             │            │
         │ • Semantic Paragraph Chunking   │             │            │
         │ • Ahnlich AI Proxy Embedding    │             │            │
         │ • Ahnlich Vector Store (p:1369) │             │            │
         └────────────────┬────────────────┘             │            │
                          │                              │            │
                          ▼                              │            │

```

┌──────────────────────────────────────────────────────────┐ │            │
│                 Ahnlich Vector Retrieval                 │ │            │
│  `GETSIMN` (Cosinesimilarity via Metadata Filtering)     │ │            │
└─────────────────────────────┬────────────────────────────┘ │            │
│                              │            │
├──────────────────────────────┘            │
│                                           │
▼                                           ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│       [ STRICT MODE ]           │         │       [ ENHANCED MODE ]         │
│  • Closed World Execution       │         │  • Open World Execution         │
│  • Local PDF Chunks Only        │         │  • Local PDF Chunks Context     │
│  • Mandated Internal Citations  │         │  • Tavily / Exa Web Search      │
│  • Zero-Leak Assertion Guard    │         │  • Legal Conflict Engine        │
└────────────────┬────────────────┘         └────────────────┬────────────────┘
│                                           │
└──────────────────────┬────────────────────┘
│
▼
┌──────────────────────────────────────────┐
│          LLM Response Synthesizer        │
│    (Claude / GPT-4 via SSE Streaming)    │
└─────────────────────┬────────────────────┘
│
▼
┌──────────────────────────────────────────┐
│         Frontend Response Renderer       │
│  • [Doc: File.pdf, p.X] Citation Badges  │
│  • [Web: Title, URL] Citation Badges     │
│  • Split-Screen PDF Jump & Highlight     │
│  • Conflict Alert Banners                │
└──────────────────────────────────────────┘

```

---

## 2. Environment Setup & Prerequisites

### 2.1 Services & Infrastructure Setup
- [ ] **Ahnlich AI Container Deployment**:
  - Deploy `ghcr.io/deven96/ahnlich-db:latest` on port `1369`.
  - Deploy `ghcr.io/deven96/ahnlich-ai:latest` on port `1370`.
  - Test store initialization using the Ahnlich CLI / SDK.
- [ ] **Third-Party API Provisioning**:
  - Obtain API keys for Anthropic Claude (or OpenAI GPT-4).
  - Obtain API keys for Tavily API or Serper API (web search for AI agents).
- [ ] **Environment Configurations**:
  - Configure `.env` files for both Backend and Frontend projects (`AHNLICH_HOST`, `AHNLICH_PORT`, `LLM_API_KEY`, `TAVILY_API_KEY`).

---

## 3. Granular Task Assignment by Role

### 🎨 FRONTEND DEVELOPER (React / Vite)

#### Step 1: Design System & Shared State Infrastructure
* Initialize a high-performance **React** app using **Vite**.
* Set up standard UI library primitives using Shadcn/UI, Lucide icons, and Tailwind CSS.
* Configure global state management (React Context or Zustand) to track:
  * Selected operational mode (`STRICT` vs. `ENHANCED`).
  * List of uploaded documents, active selections, and indexing statuses (`processing`, `embedded`, `error`).
  * Active chat thread and citation drawer visibility (`isOpen`, `activeCitation`).

#### Step 2: Document Workspace & File Upload UI
* Build a drag-and-drop file uploader (`react-dropzone`) validating `.pdf` file types and size parameters.
* Create a document drawer displaying real-time progress bars during uploads and vector indexing.
* Implement a document management panel with badges for page counts, file sizes, upload timestamps, and delete actions.

#### Step 3: Multi-Modal Query Bar (Text + Voice Input)
* **Text Input Component:** Build an auto-expanding text field supporting standard submit key events (`Enter` to submit vs. `Shift+Enter` for line breaks).
* **Voice Input Integration:**
  * Integrate Web Speech API (`webkitSpeechRecognition`) via `react-speech-recognition` or `react-speech-kit` to transcribe spoken voice into text in real time.
  * Implement dynamic mic state indicators: *Idle*, *Listening (pulsing animation)*, and *Processing*.
  * Provide a raw audio recorder fallback (`MediaRecorder` API) to send `.wav` payloads to `POST /api/v1/audio/transcribe` if browser Speech Recognition is unavailable.
* **Mode Selector Switch:** Build an interactive toggle control for **Strict Mode** vs. **Enhanced Mode** complete with tooltips explaining the scope boundary[cite: 1].

#### Step 4: Live Streaming Chat UI & Citation Rendering
* Implement a Server-Sent Events (SSE) listener (`EventSource` or `fetch-event-source`) to handle real-time streaming tokens and status updates (*"Parsing..."*, *"Searching vectors..."*, *"Querying Tavily..."*).
* Render streaming responses through custom Markdown components.
* Build custom renderers for inline citation badges:
  * **Internal Citation Badges:** Blue pill formatted as `📄 [Doc: File.pdf, p. 12, ¶ 2]`.
  * **External Citation Badges:** Green/Purple pill formatted as `🌐 [Web: domain.com]`.

#### Step 5: Evidence Drawer, TTS Output, & Export Utility
* Build a split-screen sliding drawer that triggers when clicking any inline citation badge.
* Display source metadata within the drawer: PDF title, page snippet, paragraph index, or external web page title, target URL, and raw text extract.
* Add text-to-speech audio controls (`window.speechSynthesis`) on every assistant response block to play, pause, or stop reading answers out loud.
* Create an "Export Report" feature formatting the chat thread, cited sources, and conflict logs into a downloadable PDF/Markdown report.

---

### ⚙️ BACKEND DEVELOPER 1 (FastAPI, Ingestion, Ahnlich Infrastructure & Vector Storage)

#### Step 1: Environment Setup & PDF Ingestion Microservice
* Set up Python 3.11+ project using `Poetry` or `pipenv`.
* Install core dependencies: `fastapi`, `uvicorn`, `pydantic`, `pymupdf` (PyMuPDF), `httpx`, `python-dotenv`, `ahnlich-client`.
* Create `app/services/pdf_processor.py`:
  * Integrate `PyMuPDF` or `pdfplumber` to extract document text while preserving page and structural metadata (`doc_id`, `file_name`, `page_number`, `paragraph_index`, `char_offsets`).

#### Step 2: Semantic Chunking Strategy
* Implement a text chunker using `RecursiveCharacterTextSplitter` configured for semantic context:
  * Chunk size: ~300–500 tokens.
  * Chunk overlap: ~50 tokens.
* Attach metadata keys to every chunk string: `chunk_id`, `doc_id`, `file_name`, `page_number`, `paragraph_index`, `user_id`.

#### Step 3: Ahnlich AI Container Deployment & Vector Store Config
* Create `app/services/ahnlich_service.py` and initialize the Ahnlich vector store[cite: 1]:
  ```sql
  CREATESTORE legal_docs QUERYMODEL all-minilm-l6-v2 INDEXMODEL all-minilm-l6-v2 PREDICATES (doc_id, file_name, page_number) STOREORIGINAL

```

* Implement vector insertion helper storing text chunks alongside metadata predicates (`doc_id`, `file_name`, `page_number`, `paragraph_number`).
* Implement batching scripts to push extracted chunk text arrays into the Ahnlich store.

#### Step 4: Strict Retrieval APIs & Management Endpoints

* Create `POST /api/v1/documents/upload` to validate files, extract text, perform chunking, and execute Ahnlich vector insertion.
* Create `POST /api/v1/search/strict` that:
1. Accepts user query strings and target `doc_ids`.
2. Embeds query text via Ahnlich proxy.
3. Executes `GETSIMN` cosine similarity queries against Ahnlich Vector DB with predicate filters.
4. Returns top-$K$ matching chunks with page and paragraph metadata.


* Create document management endpoints: `GET /api/v1/documents` and `DELETE /api/v1/documents/{doc_id}` (removing vector keys from Ahnlich).

#### Step 5: Audio Transcription & Performance Caching

* Build endpoint `POST /api/v1/audio/transcribe` using Whisper (`openai-whisper` or Faster-Whisper) for audio uploads from browsers without native Speech API support.
* Implement Redis key-value caching to store vector search results for identical query strings, reducing response latency.

---

### 🧠 BACKEND DEVELOPER 2 (FastAPI Router, Agent Routing, Web Search & Synthesis)

#### Step 1: LLM Infrastructure & Strict Mode Prompts

* Connect FastAPI backend to model providers (Anthropic Claude 3.5, OpenAI GPT-4o, or Ollama/Llama 3).
* Create `app/services/rag_service.py` and draft/validate **Strict Mode** system prompts:
> *"You are SIFT.AI, a legal research assistant operating in Strict Mode. Answer the query using ONLY the provided document chunks. Every claim MUST include an internal citation format: [Doc: {file_name}, p. {page_number}, ¶ {paragraph_index}]. If the information is not present, explicitly state: 'Information not found in uploaded documents'."*



#### Step 2: Agentic Query Router Engine (FastAPI)

* Build the core stream controller `POST /api/v1/chat/stream` in `app/api/v1/query.py`:
* Read input payload: `{ "query": "...", "mode": "strict" | "enhanced", "doc_ids": [...] }`.
* **If `mode == "strict"`:** Route query exclusively to Backend 1's Ahnlich vector search (`query_strict_mode`) and stream output through the strict LLM prompt.
* **If `mode == "enhanced"`:** Route payload through the hybrid agent pipeline (`query_enhanced_mode`).



#### Step 3: External Web Search Agent Integration (Enhanced Mode)

* Create `app/services/web_search.py` and integrate Tavily API or Serper API for LLM-optimized web searching.
* Build a **Query Reformulator**: An LLM call that analyzes the query and PDF context, identifies legal knowledge gaps or temporal updates, and formulates targeted web queries.
* Execute external web search, retrieve cleaned text snippets, page titles, and source URLs.

#### Step 4: Hybrid Synthesis & Conflict Flagging Engine

* Create an **Aggregator System Prompt** merging:
* Internal PDF chunks labeled as `INTERNAL_SOURCE` (with page/paragraph tags).
* Web snippets labeled as `EXTERNAL_SOURCE` (with URL tags).


* Implement the **Legal Conflict Detection Module**: Instruct the LLM to cross-reference document terms against web updates (e.g., outdated statutes or overturned precedents) and output structured conflict alerts when discrepancies occur.
* Enforce distinct citation formatting: `[Doc: {file}, p. X]` vs `[Web: {title}]({url})`.

#### Step 5: Server-Sent Events (SSE) & Security Guardrails

* Implement Python async generator using `sse-starlette` to stream tokens, execution steps (*"Searching vectors..."*, *"Checking web..."*), and parsed citation objects in real time.
* **Zero-Leak Validation Unit:** Build an output assertion check stripping any external links or non-PDF citations if the query was submitted under `STRICT` mode.

---

## 4. Sprint Execution Schedule

| Timeline | Milestone Focus | Deliverables & Responsibilities |
| --- | --- | --- |
| **Weeks 1–2** | **Foundation & Strict Mode** | • **Dev 1:** Deploy Ahnlich containers, build PyMuPDF parser, configure Ahnlich vector store & upload APIs.<br>

<br>• **Dev 2:** Setup FastAPI server, connect LLM engine, draft Strict Mode prompts, build SSE streaming setup.<br>

<br>• **Frontend:** Setup React (Vite) app, build drag-and-drop dropzone, mode switch UI, and chat interface. |
| **Weeks 3–4** | **Enhanced Mode & Mode Router** | • **Dev 1:** Build strict vector retrieval endpoints and setup Redis query caching.<br>

<br>• **Dev 2:** Implement FastAPI dual-mode query router, Tavily web search integration, and hybrid prompt.<br>

<br>• **Frontend:** Build Speech-to-Text mic input, inline citation badges, and split-screen PDF evidence drawer. |
| **Weeks 5–6** | **Conflict Engine & Demo Polish** | • **Dev 1:** Build Whisper audio transcription endpoint and optimize Ahnlich queries.<br>

<br>• **Dev 2:** Implement legal conflict detection logic and zero-leak security guardrails.<br>

<br>• **Frontend:** Build visual conflict alert banners, Text-to-Speech output, export report feature, and finalize UI polish. |

---

## 5. Master Actionable Checklist

### Frontend Developer Checklist (React / Vite)

* [ ] Initialize React + Vite project with Tailwind CSS and Radix UI primitives.
* [ ] Implement global state management tracking mode (`STRICT` vs. `ENHANCED`), documents, and citations.
* [ ] Build drag-and-drop PDF dropzone with progress indicators and list management.
* [ ] Build multi-modal query bar with auto-resizing input and Speech-to-Text voice integration.
* [ ] Build Strict / Enhanced mode toggle control with descriptive tooltips.
* [ ] Build real-time chat interface connected to backend SSE streaming endpoints.
* [ ] Build custom renderers for `InternalCitation` and `ExternalCitation` badges.
* [ ] Build split-screen PDF evidence drawer jumping directly to cited pages upon click.
* [ ] Build visual conflict alert banner component.
* [ ] Add Text-to-Speech (TTS) audio controls on assistant response messages.
* [ ] Build export report tool saving transcripts and citations as PDF/Markdown documents.

### Backend Developer 1 Checklist (FastAPI / Ingestion & Ahnlich)

* [ ] Set up FastAPI project structure with Pydantic schemas.
* [ ] Deploy `ahnlich-db` (port 1369) and `ahnlich-ai` (port 1370) Docker instances.
* [ ] Build PDF parser extracting text with page and paragraph metadata using `PyMuPDF`.
* [ ] Build semantic recursive text chunker (~300–500 tokens).
* [ ] Implement Ahnlich store creation, embedding generation, and batch vector insertion.
* [ ] Implement `POST /api/v1/documents/upload` endpoint.
* [ ] Implement `POST /api/v1/search/strict` vector similarity search endpoint using `GETSIMN`.
* [ ] Implement document deletion (`DELETE /api/v1/documents/{doc_id}`) removing entries from Ahnlich.
* [ ] Build `POST /api/v1/audio/transcribe` Whisper endpoint as voice input fallback.
* [ ] Configure Redis query embedding cache to lower latency.

### Backend Developer 2 Checklist (FastAPI / Router & Agent Engine)

* [ ] Set up LLM SDK integration (Claude 3.5 / GPT-4o) in FastAPI with strict output formatting.
* [ ] Draft and test Strict Mode system prompts requiring exact page/paragraph citations.
* [ ] Implement central query router on `POST /api/v1/chat/stream`.
* [ ] Integrate Tavily API / Serper API for LLM-optimized web searching.
* [ ] Build query reformulator generating web search queries from context gaps.
* [ ] Implement hybrid response synthesis engine combining PDF context and web snippets.
* [ ] Implement Legal Conflict Detection Engine cross-referencing PDF contracts against web data.
* [ ] Configure `sse-starlette` for token-by-token response streaming.
* [ ] Implement zero-leak security guardrail verifying no external data enters Strict Mode outputs.

```

```