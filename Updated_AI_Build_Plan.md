# Sift.ai - Comprehensive Task Breakdown & Assignment

## FRONTEND DEVELOPER

- [ ] **Step 1: Design System & Shared State Infrastructure**
  - [ ] Set up standard UI library primitives (Shadcn/UI, Lucide icons, Tailwind CSS).
  - [ ] Configure global state management (React Context or Zustand) to track:
    - [ ] Selected mode (STRICT vs. ENHANCED).
    - [ ] List of uploaded documents and processing statuses (processing, embedded, error).
    - [ ] Active conversation thread and citation drawer visibility (isOpen, active Citation).

- [ ] **Step 2: Document Management & Upload UI**
  - [ ] Build a drag-and-drop file uploader (react-dropzone) that validates .pdf file types and size limits.
  - [ ] Create a document drawer showing progress bars during uploads and vector indexing.
  - [ ] Implement a document list panel with badges displaying page count, file size, upload time, and a delete action trigger.

- [ ] **Step 3: Multi-Modal Query Bar (Text + Voice)**
  - [ ] Text Input: Build an auto-resizing text area with submit key listeners (Enter vs. Shift+Enter line breaks).
  - [ ] Voice Input:
    - [ ] Integrate Web Speech API (webkitSpeechRecognition) to transcribe user voice to text in real time.
    - [ ] Add visual mic state transitions: Idle, Listening (pulsing animation), and Processing.
    - [ ] Fall back to raw audio recorder (MediaRecorder API) to send .wav payloads to the backend if browser native speech-to-text is unavailable.
  - [ ] Mode Switcher: Build an interactive toggle bar for Strict Mode vs. Enhanced Mode with a descriptive tooltip explaining the scope boundary.

- [ ] **Step 4: Live Chat & Citation Rendering Engine**
  - [ ] Implement Server-Sent Events (SSE) listener (EventSource or fetch-event-source) to handle real-time streaming tokens and status steps ("Parsing...", "Searching vectors...", "Querying Tavily...").
  - [ ] Parse streaming responses into custom Markdown components.
  - [ ] Build custom renderers for inline citation tags:
    - [ ] Internal Citation Badges: Blue badge formatted as [Doc: File.pdf, Page: 12].
    - [ ] External Citation Badges: Green/Orange badge formatted as [Web: domain.com].

- [ ] **Step 5: Evidence Drawer & Text-to-Speech (TTS) Output**
  - [ ] Build a split-screen sliding drawer that triggers when clicking any citation badge.
  - [ ] Display source metadata inside the drawer: PDF title, page snippet, paragraph index, or web page title, URL, and raw extract.
  - [ ] Add text-to-speech audio controls (window.speechSynthesis) on every response block to play, pause, or stop reading answers out loud.
  - [ ] Add an "Export Report" button that formats the chat thread and citations into a downloadable Markdown/PDF file.

---

## BACKEND DEVELOPER 1 (Ingestion, Ahnlich Infrastructure & Vector DB)

- [ ] **Step 1: Environment & Processing Microservice**
  - [ ] Set up a FastAPI environment with pydantic schemas for incoming file upload payloads.
  - [ ] Integrate PyMuPDF or pdfplumber to extract text while maintaining strict metadata bounds per page (e.g., document_name, page_number, bounding_boxes, paragraph_index).

- [ ] **Step 2: Chunking Pipeline Strategy**
  - [ ] Build a text chunker using Recursive CharacterTextSplitter configured for semantic boundaries:
    - [ ] Chunk size: ~500 tokens.
    - [ ] Chunk overlap: ~100 tokens.
  - [ ] Attach metadata keys to every chunk string:
    - [ ] chunk_id, document_id, page_number, user_id.

- [ ] **Step 3: Ahnlich AI & Store Configuration**
  - [ ] Install ahnlich-client-py gRPC SDK and connect to local/remote Ahnlich AI proxy instances.
  - [ ] Initialize an Ahnlich store configured with an embedding model (e.g., ONNX model via Ahnlich AI proxy) and similarity metric (Cosine or Dot Product).
  - [ ] Build a batching script to push extracted chunk text arrays along with metadata predicates into the Ahnlich Vector Store.

- [ ] **Step 4: Strict Retrieval APIs & Filtering**
  - [ ] Create endpoint POST /api/v1/documents/upload to handle file validation, text extraction, chunking, and Ahnlich insertion.
  - [ ] Create endpoint POST /api/v1/search/strict that:
    - [ ] Accepts user query strings.
    - [ ] Embeds query text via Ahnlich proxy.
    - [ ] Queries Ahnlich Vector DB using metadata predicates (user_id, specific document_id).
    - [ ] Returns top-$K$ matched text chunks with page citations and similarity score thresholds.
  - [ ] Create document management endpoints: GET /api/v1/documents and DELETE /api/v1/documents/{doc_id} (which removes vector keys from Ahnlich).

- [ ] **Step 5: Audio Processing Endpoint & Optimization**
  - [ ] Create endpoint POST /api/v1/audio/transcribe using Whisper (openai-whisper or Faster-Whisper API) to handle audio uploads from browsers without Web Speech support.
  - [ ] Set up Redis key-value caching to store vector search results for identical query strings to decrease response latency.

---

## BACKEND DEVELOPER 2 (Agent Router, Web Search & Response Synthesis)

- [ ] **Step 1: Base LLM & Strict Mode System Prompts**
  - [ ] Connect to model provider endpoints (OpenAI GPT-4o, Anthropic Claude, or Ollama/Llama).
  - [ ] Draft and test Strict Mode system prompts:
    - [ ] Force the model to answer only using provided document chunks.
    - [ ] Require exact inline citation formats (e.g., [Doc: {doc_name}, Page: {page}]).
    - [ ] Return strict fallback statements ("Information not found in uploaded documents") when similarity scores are low or context is insufficient.

- [ ] **Step 2: Agentic Query Router Pipeline**
  - [ ] Build the core request controller POST /api/v1/chat/stream:
    - [ ] Read input JSON payload: { query, mode: "STRICT" | "ENHANCED", document_ids }.
    - [ ] If mode == "STRICT": Directly invoke Backend 1's strict search endpoint and pass results to the strict LLM prompt.
    - [ ] If mode == "ENHANCED": Route payload through the hybrid agent pipeline.

- [ ] **Step 3: Web Search Agent Integration (Enhanced Mode)**
  - [ ] Integrate Tavily API or Exa AI SDK for LLM-optimized web searching.
  - [ ] Build a Query Reformulator: An LLM call that takes user queries and PDF context, identifies knowledge gaps or temporal questions (e.g., updated medical guidelines or new case laws), and generates 1-2 web search queries.
  - [ ] Execute external web search, retrieve top $N$ cleaned text snippets, and capture target page URLs and domains.

- [ ] **Step 4: Hybrid Synthesis & Citation Mapping**
  - [ ] Create an Aggregator Prompt combining:
    - [ ] Local PDF chunks (labeled as INTERNAL_SOURCE).
    - [ ] Live Web snippets (labeled as EXTERNAL_SOURCE).
  - [ ] Command the LLM to synthesize both sources into a unified response, forcing it to label claims with respective source indicators:
    - [ ] [Doc: {filename}, Page: {page}] for internal PDF facts.
    - [ ] [Web: {domain_name}] ({url}) for web search facts.

- [ ] **Step 5: Server-Sent Events (SSE) & Security Guardrails**
  - [ ] Refactor response generation into a Python async generator using sse-starlette to stream tokens to the frontend in real time.
  - [ ] Implement status logs into the stream (e.g., event: status, data: "Searching web sources...").
  - [ ] Zero-Leak Validation Unit: Add an output assertion check that strips any external links or non-PDF citations if the query was processed under STRICT mode.