"""Tests for the Cloudflare R2 storage service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.storage import (
    NoopStorageService,
    R2StorageService,
    create_storage_service,
)


# ---------------------------------------------------------------------------
# NoopStorageService
# ---------------------------------------------------------------------------

async def test_noop_upload_pdf_does_not_raise() -> None:
    await NoopStorageService().upload_pdf("doc-123", b"%PDF-1.4")


async def test_noop_get_pdf_bytes_returns_none() -> None:
    result = await NoopStorageService().get_pdf_bytes("doc-123")
    assert result is None


async def test_noop_delete_pdf_does_not_raise() -> None:
    await NoopStorageService().delete_pdf("doc-123")


# ---------------------------------------------------------------------------
# R2StorageService — all boto3 calls are mocked
# ---------------------------------------------------------------------------

@patch("app.services.storage.boto3")
async def test_r2_upload_calls_put_object(mock_boto3: MagicMock) -> None:
    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    svc = R2StorageService(
        endpoint_url="https://acct.r2.cloudflarestorage.com",
        access_key_id="key",
        secret_access_key="secret",
        bucket_name="test-bucket",
    )
    await svc.upload_pdf("doc-abc", b"%PDF-1.4 content")

    mock_s3.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="pdfs/doc-abc.pdf",
        Body=b"%PDF-1.4 content",
        ContentType="application/pdf",
    )


@patch("app.services.storage.boto3")
async def test_r2_upload_does_not_raise_on_s3_error(mock_boto3: MagicMock) -> None:
    """Upload failure must be non-fatal (logged but not re-raised)."""
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = Exception("S3 connection refused")
    mock_boto3.client.return_value = mock_s3

    svc = R2StorageService("https://x.r2.cloudflarestorage.com", "k", "s", "b")
    await svc.upload_pdf("doc-err", b"%PDF")  # must not raise


@patch("app.services.storage.boto3")
async def test_r2_get_pdf_bytes_returns_content(mock_boto3: MagicMock) -> None:
    mock_s3 = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b"%PDF-1.4 binary content"
    mock_s3.get_object.return_value = {"Body": mock_body}
    mock_boto3.client.return_value = mock_s3

    svc = R2StorageService("https://x.r2.cloudflarestorage.com", "k", "s", "b")
    result = await svc.get_pdf_bytes("doc-abc")

    assert result == b"%PDF-1.4 binary content"
    mock_s3.get_object.assert_called_once_with(Bucket="b", Key="pdfs/doc-abc.pdf")


@patch("app.services.storage.boto3")
async def test_r2_get_pdf_bytes_returns_none_on_error(mock_boto3: MagicMock) -> None:
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("NoSuchKey")
    mock_boto3.client.return_value = mock_s3

    svc = R2StorageService("https://x.r2.cloudflarestorage.com", "k", "s", "b")
    result = await svc.get_pdf_bytes("missing-doc")
    assert result is None


@patch("app.services.storage.boto3")
async def test_r2_delete_calls_delete_object(mock_boto3: MagicMock) -> None:
    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    svc = R2StorageService("https://x.r2.cloudflarestorage.com", "k", "s", "b")
    await svc.delete_pdf("doc-abc")

    mock_s3.delete_object.assert_called_once_with(Bucket="b", Key="pdfs/doc-abc.pdf")


@patch("app.services.storage.boto3")
async def test_r2_delete_does_not_raise_on_error(mock_boto3: MagicMock) -> None:
    mock_s3 = MagicMock()
    mock_s3.delete_object.side_effect = Exception("R2 unavailable")
    mock_boto3.client.return_value = mock_s3

    svc = R2StorageService("https://x.r2.cloudflarestorage.com", "k", "s", "b")
    await svc.delete_pdf("doc-abc")  # must not raise


# ---------------------------------------------------------------------------
# create_storage_service factory
# ---------------------------------------------------------------------------

def test_factory_returns_noop_when_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("R2_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
    assert isinstance(create_storage_service(), NoopStorageService)


def test_factory_returns_noop_when_partial_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://x.r2.cloudflarestorage.com")
    monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
    assert isinstance(create_storage_service(), NoopStorageService)


def test_factory_returns_r2_when_all_credentials_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://x.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "my-bucket")
    assert isinstance(create_storage_service(), R2StorageService)


def test_factory_uses_default_bucket_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://x.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.delenv("R2_BUCKET_NAME", raising=False)
    svc = create_storage_service()
    assert isinstance(svc, R2StorageService)
    assert svc._bucket_name == "sift-ai-pdfs"
