"""Generation endpoint forwards credentials and maps provider failures."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def should_return_generated_content(client) -> None:
    with patch("docpipe.rag.pipeline.create_llm") as create_llm:
        model = MagicMock()
        model.invoke.return_value = MagicMock(content="Photosynthesis Overview")
        create_llm.return_value = model
        response = client.post(
            "/generate",
            json={
                "prompt": "Generate a 3-5 word title for: photosynthesis",
                "llm_provider": "openai",
                "llm_model": "gpt-4o-mini",
            },
        )
    assert response.status_code == 200
    assert response.json()["content"] == "Photosynthesis Overview"
    create_llm.assert_called_with("openai", "gpt-4o-mini", None)


def should_forward_request_api_key(client) -> None:
    with patch("docpipe.rag.pipeline.create_llm") as create_llm:
        model = MagicMock()
        model.invoke.return_value = MagicMock(content="Result")
        create_llm.return_value = model
        response = client.post(
            "/generate",
            json={
                "prompt": "hello",
                "llm_provider": "anthropic",
                "llm_model": "claude-3-5-haiku-latest",
                "api_key": "sk-ant-test",
            },
        )
    assert response.status_code == 200
    create_llm.assert_called_with("anthropic", "claude-3-5-haiku-latest", "sk-ant-test")


def should_return_400_for_unknown_provider(client) -> None:
    response = client.post(
        "/generate",
        json={"prompt": "hello", "llm_provider": "nonexistent", "llm_model": "some-model"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "configuration"


def should_return_500_for_provider_error(client) -> None:
    with patch("docpipe.rag.pipeline.create_llm") as create_llm:
        model = MagicMock()
        model.invoke.side_effect = RuntimeError("provider timeout")
        create_llm.return_value = model
        response = client.post(
            "/generate",
            json={"prompt": "hello", "llm_provider": "openai", "llm_model": "gpt-4o-mini"},
        )
    assert response.status_code == 500
