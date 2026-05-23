from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from docpipe.server.app import create_app
from docpipe.speech.types import TranscribeResult


@pytest.fixture()
def client():
    return TestClient(create_app())


def test_transcribe_openai_backend(client):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"RIFF")
        tmp.flush()
        path = tmp.name

    try:
        mock_result = TranscribeResult(text="hello world", backend="openai")
        with (
            patch(
                "docpipe.speech.service.TranscriptionService.atranscribe_file",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_transcribe,
            open(path, "rb") as audio,
        ):
            resp = client.post(
                "/transcribe",
                files={"file": ("clip.wav", audio, "audio/wav")},
                data={"backend": "openai", "output_format": "plain"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] == "hello world"
        assert body["backend"] == "openai"
        mock_transcribe.assert_awaited_once()
    finally:
        os.unlink(path)


def test_transcribe_requires_file(client):
    resp = client.post("/transcribe", data={"backend": "openai"})
    assert resp.status_code == 400


@patch("docpipe.speech.backends.openai_whisper.transcribe_file")
def test_transcription_service_openai(mock_transcribe):
    from docpipe.config import get_settings
    from docpipe.speech.service import TranscriptionService

    mock_transcribe.return_value = TranscribeResult(text="hi", backend="openai")
    settings = get_settings()
    result = TranscriptionService.transcribe_file(
        "/tmp/x.wav",
        settings=settings,
        backend="openai",
        api_key="sk-test",
    )
    assert result.text == "hi"
    mock_transcribe.assert_called_once()
