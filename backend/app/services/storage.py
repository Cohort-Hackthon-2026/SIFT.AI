"""Cloudflare R2 (S3-compatible) storage for uploaded PDFs.

PDFs are persisted under the key ``pdfs/{document_id}.pdf`` inside the
configured bucket.  The ``/api/v1/documents/{id}/file`` endpoint streams
the raw PDF back to the frontend PDF viewer so it can deep-link to cited
pages without needing external presigned-URL redirects.

Falls back to ``NoopStorageService`` when R2 credentials are absent so the
rest of the API still boots and works (documents remain searchable, the
file-serve endpoint simply returns 404).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Protocol

import boto3  # hard dependency via pyproject.toml

logger = logging.getLogger(__name__)


class StorageProtocol(Protocol):
    async def upload_pdf(self, document_id: str, pdf_bytes: bytes) -> None: ...

    async def get_pdf_bytes(self, document_id: str) -> bytes | None: ...

    async def delete_pdf(self, document_id: str) -> None: ...


class NoopStorageService:
    """Used when R2 credentials are not fully configured."""

    async def upload_pdf(self, document_id: str, pdf_bytes: bytes) -> None:
        logger.warning(
            "NoopStorageService: PDF for %s not persisted. "
            "Set R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY to enable.",
            document_id,
        )

    async def get_pdf_bytes(self, document_id: str) -> bytes | None:
        return None

    async def delete_pdf(self, document_id: str) -> None:
        pass


class R2StorageService:
    """Cloudflare R2 storage via the S3-compatible API (boto3).

    boto3 is synchronous; each method wraps its I/O in
    ``asyncio.get_running_loop().run_in_executor(None, ...)`` so it never
    blocks the FastAPI event loop.
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._bucket_name = bucket_name

    def _make_client(self):  # called from thread pool, returns a boto3 S3 client
        return boto3.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            region_name="auto",
        )

    @staticmethod
    def _pdf_key(document_id: str) -> str:
        return f"pdfs/{document_id}.pdf"

    async def upload_pdf(self, document_id: str, pdf_bytes: bytes) -> None:
        key = self._pdf_key(document_id)

        def _do() -> None:
            self._make_client().put_object(
                Bucket=self._bucket_name,
                Key=key,
                Body=pdf_bytes,
                ContentType="application/pdf",
            )

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, _do)
            logger.info("Uploaded PDF %s → R2 %s/%s", document_id, self._bucket_name, key)
        except Exception as exc:
            # Non-fatal: document is still indexed in Ahnlich + Postgres.
            # The /file endpoint will return 404 until the PDF lands in R2.
            logger.error("R2 upload failed for %s: %s", document_id, exc)

    async def get_pdf_bytes(self, document_id: str) -> bytes | None:
        """Fetch raw PDF bytes directly from R2 (streams through the API server)."""
        key = self._pdf_key(document_id)

        def _do() -> bytes:
            resp = self._make_client().get_object(Bucket=self._bucket_name, Key=key)
            return resp["Body"].read()

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, _do)
        except Exception as exc:
            logger.error("R2 download failed for %s: %s", document_id, exc)
            return None

    async def delete_pdf(self, document_id: str) -> None:
        key = self._pdf_key(document_id)

        def _do() -> None:
            self._make_client().delete_object(Bucket=self._bucket_name, Key=key)

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, _do)
            logger.info("Deleted PDF %s from R2", document_id)
        except Exception as exc:
            logger.warning("R2 delete failed for %s: %s", document_id, exc)


def create_storage_service() -> StorageProtocol:
    endpoint_url = os.getenv("R2_ENDPOINT_URL")
    access_key_id = os.getenv("R2_ACCESS_KEY_ID")
    secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("R2_BUCKET_NAME", "sift-ai-pdfs")

    if not all([endpoint_url, access_key_id, secret_access_key]):
        logger.warning(
            "R2 credentials incomplete — PDF file storage disabled. "
            "GET /documents/{id}/file will return 404."
        )
        return NoopStorageService()

    return R2StorageService(
        endpoint_url=endpoint_url,  # type: ignore[arg-type]
        access_key_id=access_key_id,  # type: ignore[arg-type]
        secret_access_key=secret_access_key,  # type: ignore[arg-type]
        bucket_name=bucket_name,
    )
