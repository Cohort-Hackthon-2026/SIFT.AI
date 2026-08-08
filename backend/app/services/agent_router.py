# app/services/agent_router.py
import json
import logging
import os
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class AgentRouterService:
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
                temperature=0.0,
            )
        else:
            self.llm = None

    async def _invoke_with_fallback(self, messages: List[Any]) -> Any:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        candidates = [self.model_name] + [m for m in self.FALLBACK_MODELS if m != self.model_name]
        last_exc = None
        for model in candidates:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=self.api_key,
                    temperature=0.0,
                )
                return await llm.ainvoke(messages)
            except Exception as exc:
                last_exc = exc
                logger.warning(f"[AgentRouter] Gemini model '{model}' failed: {exc}")
        
        raise last_exc or RuntimeError("All Gemini models failed")

    async def reformulate_query(
        self,
        user_query: str,
        internal_chunks: List[Dict[str, Any]],
    ) -> str:
        """
        Takes the user prompt + internal document context, and generates 1 targeted search query
        for Exa AI to locate relevant legal precedents or statutory updates.
        """
        if not self.api_key:
            return user_query

        context_summary = ""
        for chunk in internal_chunks[:3]:
            context_summary += chunk.get("text", "")[:200] + " "

        system_prompt = (
            "You are a legal research query reformulator. "
            "Given a user query and brief internal PDF contract context, formulate ONE concise, search-engine-optimized query "
            "to find relevant legal precedents, statutes, or appellate court rulings on the web. "
            "Return ONLY the plain text search query."
        )

        user_content = f"User Query: {user_query}\nContext Snippets: {context_summary.strip()}"

        try:
            response = await self._invoke_with_fallback([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content)
            ])
            return str(response.content).strip()
        except Exception as e:
            logger.error(f"Failed to reformulate query: {e}")
            return user_query

    async def detect_legal_conflicts(
        self,
        internal_chunks: List[Dict[str, Any]],
        web_snippets: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Compares uploaded contract clauses against retrieved live web search highlights.
        Returns a ConflictAlert dictionary if a contradiction is detected, or None.
        """
        if not self.api_key or not internal_chunks or not web_snippets:
            return None

        formatted_internal = "\n".join([f"- {c.get('text', '')[:300]}" for c in internal_chunks[:4]])
        formatted_external = "\n".join([f"- {w.get('highlights', '')[:300]}" for w in web_snippets[:4]])

        system_prompt = """You are a legal conflict detector.
Compare the uploaded contract clauses [INTERNAL] against recent legal rulings or statutes from the web [EXTERNAL].
If there is a clear contradiction or legal risk (e.g. invalid contract clause, superseded regulation), return a JSON object with:
{
  "has_conflict": true,
  "severity": "HIGH" | "MEDIUM" | "LOW",
  "contract_clause": "Summary of conflicting clause from document",
  "legal_precedent": "Summary of external legal ruling or statute",
  "explanation": "Brief explanation of the conflict"
}

If NO conflict or contradiction exists, return ONLY:
{
  "has_conflict": false
}
"""

        user_content = f"INTERNAL CLAUSES:\n{formatted_internal}\n\nEXTERNAL RULINGS:\n{formatted_external}"

        try:
            response = await self._invoke_with_fallback([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content)
            ])
            raw_text = str(response.content).strip()
            
            # Clean JSON formatting if wrapped in code blocks
            if raw_text.startswith("```"):
                parts = raw_text.split("```")
                if len(parts) > 1:
                    raw_text = parts[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            if parsed.get("has_conflict"):
                return parsed
            return None
        except Exception as e:
            logger.error(f"Failed to detect legal conflicts: {e}")
            return None
