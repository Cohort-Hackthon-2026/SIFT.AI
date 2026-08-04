# app/services/agent_router.py
import json
import os
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage


class AgentRouterService:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gemini-1.5-pro")
        
        if self.api_key:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=0.0,
            )
        else:
            self.llm = None

    async def reformulate_query(
        self,
        user_query: str,
        internal_chunks: List[Dict[str, Any]],
    ) -> str:
        """
        Takes the user prompt + internal document context, and generates 1 targeted search query
        for Exa AI to locate relevant legal precedents or statutory updates.
        """
        if not self.llm:
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
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content)
            ])
            return str(response.content).strip()
        except Exception:
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
        if not self.llm or not internal_chunks or not web_snippets:
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
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content)
            ])
            raw_text = str(response.content).strip()
            
            # Clean JSON formatting if wrapped in code blocks
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            if parsed.get("has_conflict"):
                return parsed
            return None
        except Exception:
            return None
