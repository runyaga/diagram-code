"""LLM configuration."""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OLLAMA = "ollama"

    @classmethod
    def from_env(cls) -> "ModelProvider":
        """Detect provider from environment."""
        explicit = os.getenv("LLM_PROVIDER", "").lower()
        if explicit == "ollama":
            return cls.OLLAMA
        if explicit == "openai":
            return cls.OPENAI
        if os.getenv("OPENAI_API_KEY"):
            return cls.OPENAI
        return cls.OLLAMA


# Default models per provider
DEFAULT_MODELS = {
    ModelProvider.OPENAI: "gpt-4.1-2025-04-14",
    ModelProvider.OLLAMA: "gpt-oss:20b",
}

# Default VLM (vision) models per provider
DEFAULT_VLM_MODELS = {
    ModelProvider.OPENAI: "gpt-4.1-2025-04-14",  # gpt-4o has vision capabilities

    ModelProvider.OLLAMA: "qwen3-vl:8b",  # Qwen3 vision model
}


@dataclass
class ModelConfig:
    """Configuration for a model."""
    provider: ModelProvider
    model: str

    @property
    def full_name(self) -> str:
        """Get the full model string for pydantic-ai."""
        return f"{self.provider.value}:{self.model}"

    def __str__(self) -> str:
        return f"{self.provider.value}/{self.model}"


def get_model_config(provider: Optional[ModelProvider] = None) -> ModelConfig:
    """Get the model configuration."""
    if provider is None:
        provider = ModelProvider.from_env()

    env_var = "OPENAI_MODEL" if provider == ModelProvider.OPENAI else "OLLAMA_MODEL"
    model = os.getenv(env_var, DEFAULT_MODELS[provider])
    return ModelConfig(provider=provider, model=model)


def get_vlm_model_config(provider: Optional[ModelProvider] = None) -> ModelConfig:
    """Get the VLM (vision) model configuration."""
    if provider is None:
        provider = ModelProvider.from_env()

    env_var = "OPENAI_VLM_MODEL" if provider == ModelProvider.OPENAI else "OLLAMA_VLM_MODEL"
    model = os.getenv(env_var, DEFAULT_VLM_MODELS[provider])
    return ModelConfig(provider=provider, model=model)


def _ensure_ollama_env():
    """Ensure OLLAMA_BASE_URL is set correctly for pydantic-ai.

    Pydantic-ai requires OLLAMA_BASE_URL with /v1 suffix.
    """
    if not os.getenv("OLLAMA_BASE_URL"):
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434/v1"
    elif not os.getenv("OLLAMA_BASE_URL", "").endswith("/v1"):
        # Add /v1 if not present
        base = os.getenv("OLLAMA_BASE_URL", "").rstrip("/")
        os.environ["OLLAMA_BASE_URL"] = f"{base}/v1"


def get_model_name(provider: Optional[ModelProvider] = None) -> str:
    """Get the model string for pydantic-ai.

    For Ollama, ensures OLLAMA_BASE_URL is set with /v1 suffix.
    """
    config = get_model_config(provider)

    if config.provider == ModelProvider.OLLAMA:
        _ensure_ollama_env()

    return config.full_name


def get_vlm_model_name(provider: Optional[ModelProvider] = None) -> str:
    """Get the VLM model string for pydantic-ai.

    For Ollama, ensures OLLAMA_BASE_URL is set with /v1 suffix.
    """
    config = get_vlm_model_config(provider)

    if config.provider == ModelProvider.OLLAMA:
        _ensure_ollama_env()

    return config.full_name


def get_ollama_base_url() -> str:
    """Get Ollama base URL."""
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if not base.endswith("/v1"):
        base = base.rstrip("/") + "/v1"
    return base


def get_current_config() -> dict:
    """Get current configuration as a dictionary."""
    provider = ModelProvider.from_env()
    model_config = get_model_config(provider)
    vlm_config = get_vlm_model_config(provider)

    config = {
        "provider": provider.value,
        "model": model_config.model,
        "model_full": model_config.full_name,
        "vlm_model": vlm_config.model,
        "vlm_model_full": vlm_config.full_name,
    }

    if provider == ModelProvider.OPENAI:
        config["api_key_set"] = bool(os.getenv("OPENAI_API_KEY"))
    else:
        config["ollama_url"] = get_ollama_base_url()

    return config


def print_config():
    """Print current configuration."""
    config = get_current_config()
    print(f"Provider: {config['provider']}")
    print(f"Model: {config['model_full']}")
    print(f"VLM Model: {config['vlm_model_full']}")
    if config["provider"] == "openai":
        print(f"API Key: {'Set' if config.get('api_key_set') else 'NOT SET'}")
    else:
        print(f"Ollama URL: {config.get('ollama_url')}")
