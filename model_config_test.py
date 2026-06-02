"""Configuration tests for the optional DeepSeek chat model."""

from __future__ import annotations

import os
from typing import Any

import graph


class DummyChatOpenAI:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


def test_deepseek_is_preferred() -> None:
    os.environ["DEEPSEEK_API_KEY"] = "test-deepseek-key"
    os.environ["DEEPSEEK_BASE_URL"] = "https://api.deepseek.com/v1"
    os.environ["DEEPSEEK_MODEL"] = "deepseek-v4-flash"
    os.environ["OPENAI_API_KEY"] = "test-openai-key"

    assert graph._can_use_llm()
    llm = graph._llm()
    assert llm.kwargs == {
        "api_key": "test-deepseek-key",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-v4-flash",
        "temperature": 0.2,
    }


def test_openai_fallback() -> None:
    os.environ["DEEPSEEK_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["OPENAI_MODEL"] = "test-openai-model"

    assert graph._can_use_llm()
    llm = graph._llm()
    assert llm.kwargs == {
        "api_key": "test-openai-key",
        "model": "test-openai-model",
        "temperature": 0.2,
    }


def test_placeholders_are_not_secrets() -> None:
    os.environ["DEEPSEEK_API_KEY"] = "your_deepseek_api_key_here"
    os.environ["OPENAI_API_KEY"] = ""

    assert not graph._can_use_llm()


def main() -> None:
    original_chat_openai = graph.ChatOpenAI
    original_environ = os.environ.copy()
    try:
        graph.ChatOpenAI = DummyChatOpenAI
        test_deepseek_is_preferred()
        test_openai_fallback()
        test_placeholders_are_not_secrets()
    finally:
        graph.ChatOpenAI = original_chat_openai
        os.environ.clear()
        os.environ.update(original_environ)

    print("Model configuration tests passed.")


if __name__ == "__main__":
    main()
