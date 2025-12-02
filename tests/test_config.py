"""Tests for configuration."""

import os
import pytest
from code_de_diagram.config import (
    ModelProvider,
    get_model_name,
    get_ollama_base_url,
    DEFAULT_MODELS,
)


class TestModelProvider:
    def test_values(self):
        assert ModelProvider.OPENAI == "openai"
        assert ModelProvider.OLLAMA == "ollama"

    def test_from_env_explicit_openai(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        assert ModelProvider.from_env() == ModelProvider.OPENAI

    def test_from_env_explicit_ollama(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert ModelProvider.from_env() == ModelProvider.OLLAMA

    def test_from_env_auto_openai(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert ModelProvider.from_env() == ModelProvider.OPENAI

    def test_from_env_default_ollama(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert ModelProvider.from_env() == ModelProvider.OLLAMA


class TestGetModelName:
    def test_openai_default(self, monkeypatch):
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        model = get_model_name(ModelProvider.OPENAI)
        assert model == f"openai:{DEFAULT_MODELS[ModelProvider.OPENAI]}"

    def test_ollama_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        model = get_model_name(ModelProvider.OLLAMA)
        assert model == f"ollama:{DEFAULT_MODELS[ModelProvider.OLLAMA]}"

    def test_openai_custom(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
        model = get_model_name(ModelProvider.OPENAI)
        assert model == "openai:gpt-4o"

    def test_ollama_custom(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
        model = get_model_name(ModelProvider.OLLAMA)
        assert model == "ollama:llama3.2"


class TestGetOllamaBaseUrl:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        url = get_ollama_base_url()
        assert url == "http://localhost:11434/v1"

    def test_custom_without_v1(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://myserver:8080")
        url = get_ollama_base_url()
        assert url == "http://myserver:8080/v1"

    def test_custom_with_v1(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://myserver:8080/v1")
        url = get_ollama_base_url()
        assert url == "http://myserver:8080/v1"

    def test_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://myserver:8080/")
        url = get_ollama_base_url()
        assert url == "http://myserver:8080/v1"
