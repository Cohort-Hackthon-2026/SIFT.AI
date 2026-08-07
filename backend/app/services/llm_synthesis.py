# app/services/llm_synthesis.py
import logging
import os
import re
from typing import List, Dict, Any, AsyncGenerator, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

STRICT_MODE_SYSTEM_PROMPT = """You are SIFT.AI, a precision legal research assistant operating in STRICT MODE (Closed World).

CRITICAL GROUNDING RULES:
1. You must answer the user query using ONLY the provided document chunks below.
2. Every claim or factual statement in your response MUST include an internal citation tag formatted exactly as: [Doc: {{document_name}}, Page: {{page_number}}].
3. Do NOT invent, assume, or extrapolate any legal facts, statutes, or external case law.
4. If the provided document chunks do NOT contain sufficient information to answer the query, you MUST reply with this exact fallback sentence and nothing else:
"Information not found in the uploaded documents."
5. Never output external web links or [Web: ...] citations in Strict Mode.

DOCUMENT CHUNKS:
{context_chunks}
"""


ENHANCED_MODE_SYSTEM_PROMPT = """You are SIFT.AI, an advanced legal research assistant operating in ENHANCED MODE (Hybrid World).

SYNTHESIS & CITATION RULES:
1. Synthesize information from both Internal Document Chunks [INTERNAL_SOURCE] and Live Web Precedents [EXTERNAL_SOURCE].
2. For claims sourced from internal documents, cite using: [Doc: {{document_name}}, Page: {{page_number}}].
3. For claims sourced from live web search, cite using: [Web: {{publisher_domain}}]({{url}}).
4. Clearly distinguish between internal case/contract facts and external legal precedents.
5. If there is a legal conflict between an uploaded document clause and live statutory/case law, explicitly highlight the discrepancy.

INTERNAL DOCUMENT CHUNKS:
{internal_chunks}

LIVE WEB PRECEDENTS & SEARCH HIGHLIGHTS:
{external_chunks}
"""


class LLMSynthesisService:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gemini-1.5-flash")
        
        if self.api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=0.1,
                streaming=True,
            )
        else:
            self.llm = None

    def validate_strict_response(self, response_text: str) -> str:
        """
        Zero-leak assertion guardrail: Strips external URLs and [Web: ...] tags if present in strict mode output.
        """
        # Strip web citation tags
        cleaned = re.sub(r'\[Web:[^\]]+\]\([^\)]+\)', '', response_text)
        # Strip raw URLs
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        return cleaned.strip()

    async def _stream_llm_with_fallback(self, messages: List[Any]) -> AsyncGenerator[str, None]:
        """Internal helper to stream from main LLM model, with fallback to gemini-1.5-flash if needed."""
        if not self.llm:
            yield "LLM service unavailable: GEMINI_API_KEY is not configured."
            return

        try:
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    yield str(chunk.content)
        except Exception as exc:
            logger.error(f"LLM streaming failed with model '{self.model_name}': {exc}. Attempting fallback...")
            # Fallback to gemini-1.5-flash as a known-stable model
            fallback_model = "gemini-1.5-flash"
            try:
                fallback_llm = ChatGoogleGenerativeAI(
                    model=fallback_model,
                    google_api_key=self.api_key,
                    temperature=0.1,
                    streaming=True,
                )
                async for chunk in fallback_llm.astream(messages):
                    if chunk.content:
                        yield str(chunk.content)
            except Exception as fb_exc:
                logger.error(f"Fallback LLM streaming also failed: {fb_exc}")
                yield f"\n[LLM Streaming Error: {exc}]"

    async def stream_strict_synthesis(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """
        Streams strict mode response tokens generated from internal vector store chunks.
        """
        if not context_chunks:
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

        async for token in self._stream_llm_with_fallback([system_msg, human_msg]):
            yield token

    async def stream_enhanced_synthesis(
        self,
        query: str,
        internal_chunks: List[Dict[str, Any]],
        external_snippets: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """
        Streams enhanced mode response tokens synthesizing internal chunks + Exa web search.
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

        async for token in self._stream_llm_with_fallback([system_msg, human_msg]):
            yield token
