# app/services/web_search.py
import os
from typing import List, Dict, Any, Optional
from exa_py import Exa


class WebSearchService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self.client = Exa(api_key=self.api_key) if self.api_key else None

    async def search_external_legal_web(
        self,
        query: str,
        num_results: int = 5,
        search_type: str = "auto",
    ) -> Dict[str, Any]:
        """
        Queries Exa AI for legal web precedents, statutory updates, and court rulings.
        Returns clean highlights, page titles, and source URLs.
        """
        if not self.client:
            return {
                "results": [],
                "error": "EXA_API_KEY is not configured",
                "warning": "Web search is disabled due to missing API key."
            }

        try:
            # Per setup_of_exa.md: contents={"highlights": True} returns query-relevant excerpts
            response = self.client.search(
                query=query,
                type=search_type,
                num_results=num_results,
                contents={"highlights": True}
            )

            formatted_results = []
            for item in response.results:
                highlights_text = ""
                if hasattr(item, "highlights") and item.highlights:
                    if isinstance(item.highlights, list):
                        highlights_text = " ".join(item.highlights)
                    else:
                        highlights_text = str(item.highlights)

                formatted_results.append({
                    "title": getattr(item, "title", "Untitled Source"),
                    "url": getattr(item, "url", ""),
                    "published_date": getattr(item, "published_date", None),
                    "highlights": highlights_text,
                    "author": getattr(item, "author", None),
                })

            return {
                "results": formatted_results,
                "query": query,
                "error": None
            }

        except Exception as e:
            return {
                "results": [],
                "error": str(e),
                "warning": f"Exa AI search failed: {str(e)}"
            }
