# app/services/image_extraction.py
"""Extracts text/descriptions from images using Gemini Vision.

Used by the document upload pipeline (documents.py) when a user uploads an
image instead of a PDF. The extracted text is chunked and vectorised just like
PDF text, making image content searchable via the same vector store.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

# Prompt instructs Gemini to extract structured text content from the image,
# preserving legal document structure where applicable.
_EXTRACTION_PROMPT = (
    "Extract all visible text from this image. "
    "If it is a legal document, preserve the document structure, headings, "
    "section numbers, and formatting. "
    "If it is a diagram, chart, or table, describe its contents in detail. "
    "If the image contains handwritten text, transcribe it as accurately as possible. "
    "Return only the extracted text content, no commentary."
)


class ImageExtractionService:
    """Wraps Gemini Vision calls for text extraction from images."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("DEFAULT_LLM_MODEL", "gemini-3.5-flash")

    async def extract_text(self, image_bytes: bytes, content_type: str = "image/jpeg") -> str:
        """Extract text from image bytes using Gemini Vision.

        Args:
            image_bytes: Raw image bytes (PNG, JPEG, WebP, TIFF).
            content_type: MIME type of the image.

        Returns:
            Extracted text as a string. Returns an empty string if extraction
            fails or the image contains no recognisable text.
        """
        if not self.api_key:
            logger.warning("Image extraction unavailable: GEMINI_API_KEY not configured")
            return ""

        import base64

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Map content type to the correct data URI prefix.
        mime = content_type or "image/jpeg"
        data_uri = f"data:{mime};base64,{b64_image}"

        message = HumanMessage(
            content=[
                {"type": "text", "text": _EXTRACTION_PROMPT},
                {"type": "image_url", "image_url": data_uri},
            ]
        )

        try:
            llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=0.0,
            )
            response = await llm.ainvoke([message])
            extracted = str(response.content).strip()
            logger.info(f"Image text extraction: {len(extracted)} chars extracted")
            return extracted
        except Exception as exc:
            logger.error(f"Image text extraction failed: {exc}")
            return ""
