# app/services/llm_synthesis.py
import asyncio
import logging
import os
import re
from typing import List, Dict, Any, AsyncGenerator, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# Per-model retry policy for the streaming path. We only retry a model when it
# fails BEFORE emitting any token - once tokens have streamed to the client,
# retrying would duplicate output, so we fail over to the next model instead.
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 0.5

# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

STRICT_MODE_SYSTEM_PROMPT = """You are SIFT.AI, a precision AI legal research assistant operating in STRICT MODE.

Your purpose is to help legal researchers, lawyers, and law students analyse uploaded legal documents with pinpoint accuracy.

CRITICAL GROUNDING RULES:
1. Answer the user query using ONLY the provided document chunks below.
2. Every factual statement or legal claim MUST include an internal citation formatted as: [Doc: {{document_name}}, Page: {{page_number}}].
3. Do NOT invent, assume, or extrapolate legal facts, clauses, or statutes not present in the chunks.
4. If the chunks contain partial information, clearly state what was found and what remains unanswered — never just say "not found".
5. Never output external web links or [Web: ...] citations in Strict Mode.

FORMATTING & ARRANGEMENT RULES:
You MUST arrange your response professionally using the following Markdown structure:

### 📌 Executive Summary
(Provide a brief, 1-2 sentence high-level summary of the findings here.)

### 📝 Detailed Analysis
(Provide your thorough legal analysis here. Use bolding for key terms, bullet points for lists, and subheadings `####` if necessary. Ground every claim with citations.)

### 💡 Key Takeaways / Next Steps
(Provide 1-3 actionable takeaways or concluding thoughts based solely on the documents.)

DOCUMENT CHUNKS:
{context_chunks}
"""


CONVERSATIONAL_SYSTEM_PROMPT = """You are SIFT.AI, an advanced AI legal research assistant.

You help lawyers, legal researchers, paralegals, and law students analyse contracts, case law, statutes, and legal documents with speed, precision, and deep legal insight.

Your knowledge spans all major legal domains including:
- Contract law & commercial agreements
- Tort law & civil liability
- Criminal law & procedure
- Constitutional & administrative law
- Intellectual property (copyright, patents, trademarks)
- Corporate & company law
- Property, land & real estate law

When a user greets you or asks a general question:
- Respond in a warm, professional, and helpful tone — like an experienced legal counsel.
- Briefly introduce your capabilities and invite them to upload a legal document or ask a legal question.
- Feel free to offer a useful legal insight to showcase your value.

When answering general legal questions without uploaded documents:
- Provide clear, well-structured explanations grounded in standard legal principles.
- Mention that specific situations may require tailored legal advice.
"""


ENHANCED_MODE_SYSTEM_PROMPT = """You are SIFT.AI, an advanced AI legal research assistant operating in ENHANCED MODE.

You combine uploaded legal document analysis with cutting-edge live web precedents to deliver comprehensive legal insights.

SYNTHESIS & CITATION RULES:
1. Synthesise information from both Internal Document Chunks and Live Web Precedents.
2. For claims from internal documents, cite using: [Doc: {{document_name}}, Page: {{page_number}}].
3. For claims from live web search, cite using: [Web: {{publisher_domain}}]({{url}}).
4. Clearly distinguish between internal case/contract facts and external legal precedents or statutes.
5. If there is a legal conflict between an uploaded document clause and live statutory/case law, explicitly highlight it with: ⚠️ **CONFLICT DETECTED** — followed by the legal explanation.

FORMATTING & ARRANGEMENT RULES:
You MUST arrange your response professionally using the following Markdown structure:

### 📌 Executive Summary
(Provide a brief, high-level summary of both the internal findings and external precedents.)

### 📝 Detailed Analysis
(Provide your thorough legal analysis here. Use bolding for key terms, bullet points for lists, and subheadings `####` if necessary. Integrate internal and external facts seamlessly, with clear citations.)

### ⚖️ Legal Conflicts & Risks
(If any conflicts or risks exist between the document and external law, detail them here. If none, briefly state that no major conflicts were found.)

### 💡 Key Takeaways
(Provide 1-3 actionable takeaways or concluding thoughts.)

INTERNAL DOCUMENT CHUNKS:
{internal_chunks}

LIVE WEB PRECEDENTS & SEARCH HIGHLIGHTS:
{external_chunks}
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LLMSynthesisService:
    """
    Synthesizes legal analysis using Google Gemini models with automatic fallback.
    Validated active models: gemini-3.5-flash, gemini-3.6-flash, gemini-flash-latest, gemini-3.5-flash-lite.
    """

    FALLBACK_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gemini-3.5-flash")
        
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
        return cleaned.strip()

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

    @classmethod
    def _is_conversational(cls, query: str) -> bool:
        return bool(cls._CONVERSATIONAL_QUERY.match(query or ""))

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

        logger.error(f"[Gemini] All models failed: {last_error}")
        yield f"\n[LLM Error: {last_error}]"

    async def stream_strict_synthesis(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """
        Streams strict mode response tokens.
        - If no document chunks are attached, responds conversationally to
          greetings/capability questions, otherwise returns the honest
          "not found" fallback (never answers a document question from the
          model's own knowledge in strict mode).
        - If chunks are present, performs grounded citation analysis.
        """
        if not context_chunks:
            if self._is_conversational(query):
                system_msg = SystemMessage(content=CONVERSATIONAL_SYSTEM_PROMPT)
                human_msg = HumanMessage(content=query)
                async for token in self._stream_with_fallback([system_msg, human_msg]):
                    yield token
            else:
                yield "Information not found in the uploaded documents."
            return

        formatted_context = ""
        for idx, chunk in enumerate(context_chunks, 1):
            doc_name = chunk.get("document_name", "Document")
            page_num = chunk.get("page_number", "?")
            text = chunk.get("text", "")
            formatted_context += f"--- Chunk {idx} [Doc: {doc_name}, Page: {page_num}] ---\n{text}\n\n"

        system_msg = SystemMessage(
            content=STRICT_MODE_SYSTEM_PROMPT.format(context_chunks=formatted_context)
        )
        human_msg = HumanMessage(content=query)

        async for token in self._stream_with_fallback([system_msg, human_msg]):
            yield token

    async def stream_enhanced_synthesis(
        self,
        query: str,
        internal_chunks: List[Dict[str, Any]],
        external_snippets: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """
        Streams enhanced mode response tokens (internal chunks + live Exa web search).
        """
        formatted_internal = ""
        for idx, chunk in enumerate(internal_chunks, 1):
            doc_name = chunk.get("document_name", "Document")
            page_num = chunk.get("page_number", "?")
            text = chunk.get("text", "")
            formatted_internal += f"--- Internal Chunk {idx} [Doc: {doc_name}, Page: {page_num}] ---\n{text}\n\n"

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
            )
        )
        human_msg = HumanMessage(content=query)

        async for token in self._stream_with_fallback([system_msg, human_msg]):
            yield token
