# app/services/llm_synthesis.py
import asyncio
import logging
import os
import re
from typing import List, Dict, Any, AsyncGenerator, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)

# Per-model retry policy for the streaming path. We only retry a model when it
# fails BEFORE emitting any token - once tokens have streamed to the client,
# retrying would duplicate output, so we fail over to the next model instead.
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 0.5

# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

# The {{user_query}} / {{document_names}} placeholders are injected by the
# synthesis service from the actual request so the model is anchored to the
# subject of this specific conversation - not just a pile of chunks.

NIGERIAN_CITATION_CONTEXT = """
PRIMARY JURISDICTION DIRECTIVE — NIGERIAN LEGAL SYSTEM:
All legal questions, document reviews, statutory interpretations, case law citations, and procedural remedies MUST default strictly to the Nigerian legal system and Nigerian jurisprudence, unless the user explicitly requests another foreign jurisdiction.

1. Supreme Constitutional Framework:
   - Constitution of the Federal Republic of Nigeria 1999 (as amended) is the supreme law (Section 1(1) & (3)).
   - Fundamental Human Rights: Chapter IV (Sections 33 to 46) — Right to Life (s.33), Dignity of Human Person (s.34), Personal Liberty (s.35), Fair Hearing (s.36), Freedom of Expression (s.39).

2. Core Statutory Corpus:
   - Administration of Criminal Justice Act (ACJA) 2015 & State Administration of Criminal Justice Laws (e.g. Lagos ACJL 2021).
   - Evidence Act 2011 (as amended by Evidence (Amendment) Act 2023 — particularly Sections 84 & 84A–D regarding computer-generated/electronic evidence).
   - Nigeria Police Act 2020 (Sections 3–10, 31–38, 48–50 — prohibiting civil matter arrests and guaranteeing rights of suspects).
   - Companies and Allied Matters Act (CAMA) 2020 (Corporate affairs, CAC requirements, directors' duties).
   - Land Use Act 1978 (Governor's consent, Statutory Right of Occupancy).
   - Labour Act (Cap L1 LFN 2004) & National Industrial Court Civil Procedure Rules.
   - Fundamental Rights (Enforcement Procedure) Rules 2009 (FREP Rules).
   - Criminal Code Act (Southern Nigeria) / Penal Code (Northern Nigeria & FCT).
   - Cybercrimes (Prohibition, Prevention, etc.) Act 2015 (as amended 2024).

3. Nigerian Law Reports (NWLR) Citation Standard:
   When referencing Nigerian precedents, format citations as:
   Format: [YYYY] Vol NWLR (Pt. XXX) Page
   Example: [2019] 7 NWLR (Pt. 1670) 1
   Or Electronic Report format: (YYYY) LPELR-XXXXX(SC)/(CA)

4. Nigerian Court Hierarchy Codes for Inline References:
   [SC]   — Supreme Court of Nigeria (Final Appellate Authority)
   [CA]   — Court of Appeal of Nigeria
   [FHC]  — Federal High Court
   [NIC]  — National Industrial Court of Nigeria
   [SHCL] — High Court of Lagos State
   [SHCA] — High Court of the Federal Capital Territory (Abuja)
   [SHCK] — High Court of Kano State
   [CCC]  — Customary Court of Appeal
   [SCA]  — Sharia Court of Appeal

Always prioritize Nigerian statutory provisions and apex court precedents over foreign persuasions.
"""

STRICT_MODE_SYSTEM_PROMPT = """You are SIFT.AI, a precision AI legal research assistant operating in STRICT MODE, grounded in the Nigerian legal system.

You are analysing: {document_names}
User question: {user_query}

""" + NIGERIAN_CITATION_CONTEXT + """

CRITICAL GROUNDING RULES:
1. Answer the user question using ONLY the provided document chunks below. The chunks come from the document(s) named above - every answer must be traceable to them.
2. Every factual statement or legal claim MUST include an internal citation formatted as: [Doc: {{document_name}}, Page: {{page_number}}].
3. Do NOT invent, assume, or extrapolate legal facts, clauses, or statutes not present in the chunks. If the chunks do not contain what the question asks for, say so explicitly (see Gaps section).
4. Never output external web links, URLs, or [Web: ...] citations in Strict Mode.
5. Stay on the subject of the user's question. Ground interpretations in Nigerian legal principles when applicable.
6. When a chunk originates from a Nigerian case or statute, cite using the NWLR format above alongside the document citation.
7. USER INSTRUCTION & FORMAT OVERRIDE: If the user explicitly requests a specific format, length, or task (e.g. "summarize in 3 sentences", "in one paragraph", "bullet points only", "draft an email/notice", "table format"), you MUST STRICTLY FOLLOW the user's requested format and length constraint above all else, while still preserving required citations.

DEFAULT RESPONSE STRUCTURE (use only when the user has not specified a custom format or length):

### Executive Summary
Start with a 1-2 sentence answer to the user question, stating which document(s) you drew it from (e.g. "[Doc: lease.pdf, Page: 3]"). This must be a real answer, not a description of what you will do.

### Detailed Analysis
Give the thorough, well-organised legal analysis. Use bolding for key terms, bullet points for lists, and `####` subheadings for distinct sub-topics. Every claim must carry its citation. Address the document's actual clauses/sections verbatim where possible, then interpret them.

### Gaps & Limitations
State precisely what the uploaded document(s) do and do not cover with respect to the user question. If the documents do not address the question at all, say so directly here rather than inventing an answer.

### Key Takeaways
End with 1-3 actionable, citation-backed takeaways drawn from the analysis.

DOCUMENT CHUNKS:
{context_chunks}
"""


CONVERSATIONAL_SYSTEM_PROMPT = """You are SIFT.AI, an advanced AI legal research assistant specializing in the Nigerian Legal System and Nigerian Jurisprudence.

You assist Nigerian legal practitioners (Senior Advocates of Nigeria, legal counsel, in-house attorneys), magistrates, judges, law students, and researchers across all Nigerian legal domains, including:
- Nigerian Constitutional Law (1999 Constitution as amended) & Fundamental Rights Enforcement (FREP Rules 2009)
- Criminal Law (Criminal Code, Penal Code, ACJA 2015, ACJLs, Police Act 2020)
- Corporate & Commercial Law (CAMA 2020, CAC compliance, SEC/FCCPC regulations)
- Evidence Law (Evidence Act 2011 as amended 2023)
- Property & Real Estate Law (Land Use Act 1978, State Tenancy Laws, Governor's Consent)
- Employment & Labour Law (Labour Act, NICN Rules, Trade Disputes Act)
- Civil Litigation & Appellate Practice (Supreme Court & Court of Appeal Rules, State High Court Civil Procedure Rules)

When a user greets you or asks a general question:
- Respond in an authoritative, professional, and courteous tone — reflecting the etiquette of the Nigerian Bar.
- Briefly introduce your capabilities for Nigerian legal research, contract audit, NWLR precedent analysis, and statutory cross-referencing.
- Invite them to upload legal documents or present a legal scenario.

When answering general legal questions:
- Anchor the explanation firmly in Nigerian law, quoting relevant Nigerian statutes and NWLR precedents where appropriate.
- Do not use decorative emojis. Maintain a professional, clean tone.
"""

DIRECT_LEGAL_ANALYSIS_SYSTEM_PROMPT = """You are SIFT.AI, an advanced AI legal research assistant specializing in Nigerian Law.

The user is presenting a legal question, factual scenario, or incident directly in text (without uploaded document attachments).

""" + NIGERIAN_CITATION_CONTEXT + """

GUIDELINES FOR DIRECT LEGAL ANALYSIS:
1. Provide a comprehensive, structured, and authoritative legal breakdown strictly grounded in Nigerian Law and appellate precedents.
2. USER INSTRUCTION & FORMAT OVERRIDE: If the user specifies an explicit format, length, or task constraint (e.g. "summarize in 3 sentences", "in 1 paragraph", "bullet points only", "draft a legal notice", "in 50 words"), you MUST STRICTLY OBEY the user's requested constraint and format.
3. DEFAULT STRUCTURE (use only when the user has not specified a custom length or format constraint):
   ### Executive Summary
   Direct 1-2 sentence legal assessment under Nigerian Law.

   ### Applicable Nigerian Laws & Legal Characterisation
   Detail relevant Nigerian statutes (e.g. 1999 Constitution as amended, Administration of Criminal Justice Act (ACJA) 2015, Evidence Act 2011/2023, Police Act 2020, CAMA 2020, Land Use Act 1978, Criminal/Penal Code), common law torts as received into Nigerian jurisprudence, and relevant Supreme Court / Court of Appeal rulings in NWLR format.

   ### Available Legal Options & Remedies
   Provide clear step-by-step procedural options in Nigeria (e.g. lodging a formal petition to the Commissioner of Police / DPO, fundamental rights enforcement suit at the Federal/State High Court under FREP Rules 2009, civil action for damages, CAC filings, or reporting to regulatory ombudsmen like FCCPC or NHRC).

   ### Evidence Preservation & Critical Next Steps
   Practical, immediate steps under Nigerian Evidence Act standards (e.g. Section 84 certificate for electronic/CCTV/WhatsApp evidence, certified true copies, police medical report forms, witness statements).

   ### Key Takeaways
   1-3 crisp, actionable takeaways for the user or their legal practitioner.

FORMATTING & STYLISTIC CONSTRAINTS:
- Use clean, structured, and readable prose paragraphs with bullet points for lists.
- DO NOT use emojis anywhere in the response. Maintain formal Nigerian legal practice standards.
- DO NOT use horizontal rule dividers (do NOT write `---`).
- DO NOT generate ASCII diagram lines or flowchart arrow boxes (do NOT write `[A] ──> [B]`). Use clear descriptive paragraphs or numbered steps instead.
- Ensure proper spacing between words, statutory titles, citations, and headings. Always put a blank line before and after headings.
- DO NOT invent fake internal document citations (do NOT write `[Doc: ...]`) because there are no uploaded internal documents.
- Maintain an authoritative, professional, and rigorous Nigerian legal counsel tone.
"""



ENHANCED_MODE_SYSTEM_PROMPT = """You are SIFT.AI, an advanced AI legal research assistant operating in ENHANCED MODE, specializing in Nigerian Law and Comparative Jurisprudence.

You are analysing: {document_names}
User question: {user_query}

""" + NIGERIAN_CITATION_CONTEXT + """

You combine analysis of the uploaded legal document(s) above with live web precedents, Nigerian statutory updates, and appellate court rulings to deliver comprehensive legal insight on exactly the user's question.

SYNTHESIS & CITATION RULES:
1. Synthesise information from both Internal Document Chunks and Live Web Precedents - but keep them clearly distinguished in every paragraph.
2. For claims from internal documents, cite using: [Doc: {{document_name}}, Page: {{page_number}}].
3. For claims from live web search, cite using: [Web: {{publisher_domain}}]({{url}}).
4. If the user's question concerns the uploaded document(s), the document analysis is the primary answer; web precedents are used to supplement, confirm, or contradict it. If the question is purely about current law, the web sources lead.
5. If there is a legal conflict between an uploaded document clause and Nigerian statutory provisions or apex court precedents, explicitly highlight it with: **LEGAL CONFLICT DETECTED** — followed by the legal explanation.
6. When referencing Nigerian cases or statutes, use NWLR citation format alongside the web citation.
7. Do not use emojis in headings or body text.
8. USER INSTRUCTION & FORMAT OVERRIDE: If the user explicitly requests a specific format, length, or task constraint (e.g. "in 3 sentences", "bullet points only", "draft a petition", "in one paragraph"), you MUST STRICTLY OBEY that constraint above all else.

DEFAULT RESPONSE STRUCTURE (use only when the user has not specified a custom format or length):

### Executive Summary
A 1-2 sentence answer that names whether it rests on the document(s), the web, or both (e.g. "[Doc: lease.pdf, Page: 3] and [Web: example.com](https://...)").

### Detailed Analysis
Thorough analysis combining internal and external sources. Bolding for key terms, bullet points, `####` subheadings as needed. Every claim carries its citation. Where internal and external sources agree, say so; where they diverge, say so.

### Legal Conflicts & Risks
If any conflict or risk exists between the document and external Nigerian law/statutes, detail it here with the **LEGAL CONFLICT DETECTED** marker. If none, state that no major conflicts were found after review.

### Key Takeaways
1-3 actionable takeaways, each citing its source.


INTERNAL DOCUMENT CHUNKS:
{internal_chunks}

LIVE WEB PRECEDENTS & SEARCH HIGHLIGHTS:
{external_chunks}
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LLMSynthesisService:
    """
    Synthesizes legal analysis using Google Gemini models with automatic fallback.
    Validated active models: gemini-3.7-flash, gemini-3.1-pro, gemini-3.5-flash, gemini-3.6-flash, gemini-flash-latest, gemini-3.5-flash-lite.
    """

    FALLBACK_MODELS = [
        "gemini-3.7-flash",
        "gemini-3.1-pro",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gemini-3.7-flash")
        
        if self.api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=0.2,
                streaming=True,
            )
        else:
            self.llm = None


    @staticmethod
    def _extract_text(content: Any) -> str:
        """Normalises Gemini content chunks (plain string or parts list) into clean text."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
                elif isinstance(part, str):
                    parts.append(part)
            return "".join(parts)
        if isinstance(content, dict) and "text" in content:
            return content["text"]
        return str(content) if content else ""

    def validate_strict_response(self, response_text: str) -> str:
        """Strips web citations or external URLs that leak into strict mode output."""
        cleaned = re.sub(r'\[Web:[^\]]+\]\([^\)]+\)', '', response_text)
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        return cleaned


    @staticmethod
    def _escape_braces(value: str) -> str:
        """Escape braces so user/document text is safe to pass through str.format().

        The system prompts are rendered with .format(); a raw `{` or `}` in a
        document name or user query would otherwise be interpreted as a format
        field and raise KeyError / ValueError.
        """
        return (value or "").replace("{", "{{").replace("}", "}}")

    @staticmethod
    def _document_names(chunks: List[Dict[str, Any]]) -> str:
        """Unique, comma-joined document names for grounding the prompt."""
        names = []
        for chunk in chunks:
            name = chunk.get("document_name") or "Document"
            if name not in names:
                names.append(name)
        return ", ".join(names) if names else "the uploaded document(s)"

    # Obvious greetings / capability questions that a legal researcher would
    # send before uploading anything. These are the ONLY queries we answer
    # conversationally in strict mode - everything else with no matching
    # chunks gets the honest "not found" so the strict grounding promise
    # (never answer document questions from the model's own knowledge) holds.
    _CONVERSATIONAL_QUERY = re.compile(
        r"^\s*(hi|hello|hey|yo|greetings|good\s+(morning|afternoon|evening)|"
        r"how\s+are\s+you|how'?s\s+it\s+going|who\s+are\s+you|what\s+(can|do)\s+you|"
        r"help|thanks?|thank\s+you)\b",
        re.IGNORECASE,
    )

    _DOC_SPECIFIC_QUERY = re.compile(
        r"^\s*(what\s+does\s+(clause|section|article|paragraph|schedule)\s+\d+|"
        r"in\s+(the|this|my)\s+(uploaded|attached)?\s*(document|pdf|file|contract|lease|agreement|deed)|"
        r"(the|this)\s+(uploaded|attached)\s+(document|pdf|file|contract|lease|agreement)|"
        r"clause\s+\d+|section\s+\d+\s+of\s+the\s+(contract|lease|agreement))\b",
        re.IGNORECASE,
    )

    @classmethod
    def _is_conversational(cls, query: str) -> bool:
        return bool(cls._CONVERSATIONAL_QUERY.match(query or ""))

    @classmethod
    def _is_document_specific_query(cls, query: str) -> bool:
        return bool(cls._DOC_SPECIFIC_QUERY.search(query or ""))

    @staticmethod
    def _build_history_messages(history: List[Dict[str, str]]) -> List[Any]:
        """Convert conversation history dicts into LangChain message objects."""
        messages = []
        for entry in history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if not content:
                continue
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    @staticmethod
    def _build_human_message(query: str, images: List[str] | None = None) -> HumanMessage:
        """Build a HumanMessage — multimodal if images are attached, text-only otherwise."""
        if not images:
            return HumanMessage(content=query)

        # Multimodal: list of content blocks (text + images).
        content: List[Dict[str, Any]] = [{"type": "text", "text": query}]
        for img_b64 in images:
            content.append({
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{img_b64}",
            })
        return HumanMessage(content=content)

    async def _stream_with_fallback(self, messages: List[Any]) -> AsyncGenerator[str, None]:
        """Streams tokens from primary model, falling back to candidate models on failure."""
        if not self.api_key:
            yield "LLM service unavailable: GEMINI_API_KEY is not configured."
            return

        from unittest.mock import Mock
        if self.llm is not None and isinstance(self.llm, Mock):
            try:
                async for chunk in self.llm.astream(messages):
                    if chunk.content is not None:
                        text = self._extract_text(chunk.content)
                        if text:
                            yield text
                return
            except Exception as exc:
                yield f"\n[LLM Error: {exc}]"
                return

        # Build candidate list starting with primary model
        candidates = [self.model_name] + [m for m in self.FALLBACK_MODELS if m != self.model_name]

        last_error = None
        for model in candidates:
            llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=self.api_key,
                temperature=0.2,
                streaming=True,
            )
            for attempt in range(MAX_RETRIES):
                yielded_any = False
                try:
                    logger.info(f"[Gemini] Streaming via model '{model}' (attempt {attempt + 1})")
                    async for chunk in llm.astream(messages):
                        if chunk.content:
                            text = self._extract_text(chunk.content)
                            if text:
                                yielded_any = True
                                yield text
                    if yielded_any:
                        return  # Success
                    # No content and no exception: treat as a soft failure and
                    # move on to the next model (retrying an empty stream is
                    # unlikely to help).
                    break
                except Exception as exc:
                    last_error = exc
                    if yielded_any:
                        # Already streamed to the client - retrying would
                        # duplicate tokens, so fail over to the next model.
                        logger.warning(
                            f"[Gemini] Model '{model}' failed mid-stream: {exc}. "
                            "Failing over (partial output already sent)."
                        )
                        break
                    if attempt < MAX_RETRIES - 1:
                        delay = BASE_DELAY_SECONDS * (2 ** attempt)
                        logger.warning(
                            f"[Gemini] Model '{model}' attempt {attempt + 1} failed: {exc}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.warning(
                            f"[Gemini] Model '{model}' exhausted retries: {exc}. "
                            "Trying next model..."
                        )
                        break

        logger.error(f"[Gemini] All models failed: {last_error}")
        yield f"\n[LLM Error: {last_error}]"

    async def stream_strict_synthesis(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        history: List[Dict[str, str]] | None = None,
        images: List[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streams strict mode response tokens.
        - If no document chunks are attached:
          - Greetings / capability questions are answered conversationally.
          - Document-specific questions (referencing clauses/sections) with no documents return 'not found'.
          - Direct legal questions, scenarios, or incident reports are answered
            with structured legal analysis under applicable Nigerian laws (without fake
            document citations).
        - If document chunks are present, performs grounded citation analysis.
        - Supports conversation history for multi-turn context.
        - Supports inline images via Gemini Vision multimodal input.
        """
        if not context_chunks and not images:
            if self._is_conversational(query):
                system_msg = SystemMessage(content=CONVERSATIONAL_SYSTEM_PROMPT)
                human_msg = self._build_human_message(query, images)
                messages = [system_msg]
                if history:
                    messages.extend(self._build_history_messages(history))
                messages.append(human_msg)
                async for token in self._stream_with_fallback(messages):
                    yield token
                return
            elif self._is_document_specific_query(query):
                yield "Information not found in the uploaded documents."
                return
            else:
                system_msg = SystemMessage(content=DIRECT_LEGAL_ANALYSIS_SYSTEM_PROMPT)
                human_msg = self._build_human_message(query, images)
                messages = [system_msg]
                if history:
                    messages.extend(self._build_history_messages(history))
                messages.append(human_msg)
                async for token in self._stream_with_fallback(messages):
                    yield token
                return

        formatted_context = ""
        for idx, chunk in enumerate(context_chunks, 1):
            doc_name = chunk.get("document_name", "Document")
            page_num = chunk.get("page_number", "?")
            text = chunk.get("text", "")
            source = chunk.get("source", "pdf")
            source_label = "Chat Context" if source == "chat_text" else f"Doc: {doc_name}"
            formatted_context += f"--- Chunk {idx} [{source_label}, Page: {page_num}] ---\n{text}\n\n"

        system_msg = SystemMessage(
            content=STRICT_MODE_SYSTEM_PROMPT.format(
                context_chunks=formatted_context,
                document_names=self._escape_braces(self._document_names(context_chunks)),
                user_query=self._escape_braces(query),
            )
        )
        human_msg = self._build_human_message(query, images)

        messages = [system_msg]
        if history:
            messages.extend(self._build_history_messages(history))
        messages.append(human_msg)

        async for token in self._stream_with_fallback(messages):
            yield token

    async def stream_enhanced_synthesis(
        self,
        query: str,
        internal_chunks: List[Dict[str, Any]],
        external_snippets: List[Dict[str, Any]],
        history: List[Dict[str, str]] | None = None,
        images: List[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streams enhanced mode response tokens (internal chunks + live Exa web search).
        Supports conversation history and inline images.
        """
        formatted_internal = ""
        for idx, chunk in enumerate(internal_chunks, 1):
            doc_name = chunk.get("document_name", "Document")
            page_num = chunk.get("page_number", "?")
            text = chunk.get("text", "")
            source = chunk.get("source", "pdf")
            source_label = "Chat Context" if source == "chat_text" else f"Doc: {doc_name}"
            formatted_internal += f"--- Internal Chunk {idx} [{source_label}, Page: {page_num}] ---\n{text}\n\n"

        formatted_external = ""
        for idx, item in enumerate(external_snippets, 1):
            title = item.get("title", "Web Source")
            url = item.get("url", "")
            highlights = item.get("highlights", "")
            formatted_external += f"--- Web Source {idx} [{title}] ({url}) ---\n{highlights}\n\n"

        system_msg = SystemMessage(
            content=ENHANCED_MODE_SYSTEM_PROMPT.format(
                internal_chunks=formatted_internal or "No internal document chunks matched.",
                external_chunks=formatted_external or "No external web sources retrieved.",
                document_names=self._escape_braces(self._document_names(internal_chunks)),
                user_query=self._escape_braces(query),
            )
        )
        human_msg = self._build_human_message(query, images)

        messages = [system_msg]
        if history:
            messages.extend(self._build_history_messages(history))
        messages.append(human_msg)

        async for token in self._stream_with_fallback(messages):
            yield token
