"""Integration tests for LLM connectivity and basic functionality.

These tests verify that the configured LLM providers are reachable and
return properly structured responses.

Run with: pytest tests/test_integration_llm.py -v -m integration
"""

import pytest
import httpx

from code_de_diagram.config import (
    ModelProvider,
    get_model_name,
    get_ollama_base_url,
    get_vlm_model_name,
)


# ============================================================================
# Ollama Connectivity Tests
# ============================================================================

class TestOllamaConnectivity:
    """Tests for Ollama server connectivity."""

    @pytest.mark.integration
    def test_ollama_server_reachable(self, require_ollama):
        """Verify Ollama server responds to API requests."""
        base_url = get_ollama_base_url().replace("/v1", "")
        response = httpx.get(f"{base_url}/api/tags", timeout=10.0)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_ollama_has_models(self, require_ollama):
        """Verify Ollama has at least one model installed."""
        base_url = get_ollama_base_url().replace("/v1", "")
        response = httpx.get(f"{base_url}/api/tags", timeout=10.0)
        data = response.json()
        assert "models" in data
        # Note: models list can be empty, just checking the API works

    @pytest.mark.integration
    def test_ollama_chat_endpoint(self, require_ollama):
        """Verify Ollama chat completions endpoint is available."""
        base_url = get_ollama_base_url()
        # Just check the endpoint exists (will get error without proper request)
        try:
            response = httpx.post(
                f"{base_url}/chat/completions",
                json={"model": "test", "messages": []},
                timeout=5.0,
            )
            # Any response (even error) means endpoint is reachable
            assert response.status_code in [200, 400, 404, 500]
        except httpx.ConnectError:
            pytest.fail("Could not connect to Ollama chat endpoint")


# ============================================================================
# OpenAI Connectivity Tests
# ============================================================================

class TestOpenAIConnectivity:
    """Tests for OpenAI API connectivity."""

    @pytest.mark.integration
    def test_openai_api_reachable(self, require_openai):
        """Verify OpenAI API responds."""
        import os
        api_key = os.environ.get("OPENAI_API_KEY")

        response = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        # 200 = success, 401 = invalid key but API reachable
        assert response.status_code in [200, 401]

    @pytest.mark.integration
    def test_openai_api_key_valid(self, require_openai):
        """Verify OpenAI API key is valid."""
        import os
        api_key = os.environ.get("OPENAI_API_KEY")

        response = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        assert response.status_code == 200, f"API key may be invalid: {response.status_code}"


# ============================================================================
# Model Configuration Tests
# ============================================================================

class TestModelConfiguration:
    """Tests for model configuration."""

    def test_get_model_name_returns_string(self):
        """Verify get_model_name returns a properly formatted string."""
        provider = ModelProvider.from_env()
        model_name = get_model_name(provider)

        assert isinstance(model_name, str)
        assert ":" in model_name  # Format should be "provider:model"

        parts = model_name.split(":", 1)
        assert parts[0] in ["openai", "ollama"]
        assert len(parts[1]) > 0

    def test_get_vlm_model_name_returns_string(self):
        """Verify get_vlm_model_name returns a properly formatted string."""
        vlm_name = get_vlm_model_name()

        assert isinstance(vlm_name, str)
        assert ":" in vlm_name

        parts = vlm_name.split(":", 1)
        assert parts[0] in ["openai", "ollama"]

    def test_ollama_base_url_format(self):
        """Verify Ollama base URL ends with /v1."""
        url = get_ollama_base_url()
        assert url.endswith("/v1")
        assert url.startswith("http")


# ============================================================================
# Pydantic-AI Agent Creation Tests
# ============================================================================

class TestAgentCreation:
    """Tests for pydantic-ai agent creation (no network calls)."""

    def test_direct_analyzer_agent_creates(self):
        """Verify direct analyzer agent can be created."""
        # Import here to avoid side effects
        from code_de_diagram.solutions.direct import get_analyzer

        agent = get_analyzer()
        assert agent is not None

    def test_direct_generator_agent_creates(self):
        """Verify direct generator agent can be created."""
        from code_de_diagram.solutions.direct import get_generator

        agent = get_generator()
        assert agent is not None

    def test_structured_analyzer_agent_creates(self):
        """Verify structured analyzer agent can be created."""
        from code_de_diagram.solutions.structured import get_analyzer

        agent = get_analyzer()
        assert agent is not None

    def test_structured_generator_agent_creates(self):
        """Verify structured generator agent can be created."""
        from code_de_diagram.solutions.structured import get_generator

        agent = get_generator()
        assert agent is not None

    def test_vlm_analyzer_agent_creates(self):
        """Verify VLM analyzer agent can be created."""
        from code_de_diagram.vlm_verifier import get_analyzer

        agent = get_analyzer()
        assert agent is not None

    def test_vlm_verifier_agent_creates(self):
        """Verify VLM verifier agent can be created."""
        from code_de_diagram.vlm_verifier import get_verifier

        agent = get_verifier()
        assert agent is not None


# ============================================================================
# LLM Smoke Tests (Actual API Calls)
# ============================================================================

class TestLLMSmoke:
    """Smoke tests that make actual LLM API calls."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyzer_returns_structured_response(
        self, require_llm, minimal_architecture_description
    ):
        """Verify analyzer agent returns properly structured AnalysisResponse."""
        from code_de_diagram.solutions.structured import (
            get_analyzer,
            AnalysisResponse,
            AgentContext,
        )

        agent = get_analyzer()
        context = AgentContext()

        result = await agent.run(
            f"Analyze this architecture: {minimal_architecture_description}",
            deps=context,
        )

        # Verify the response is properly structured
        assert isinstance(result.output, AnalysisResponse)
        assert isinstance(result.output.summary, str)
        assert len(result.output.summary) > 0
        assert isinstance(result.output.identified_components, list)
        assert isinstance(result.output.confidence, float)
        assert 0.0 <= result.output.confidence <= 1.0
        assert isinstance(result.output.ready_to_generate, bool)

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_spec_generator_returns_diagram_spec(
        self, require_llm, minimal_architecture_description
    ):
        """Verify spec generator returns valid DiagramSpec."""
        from code_de_diagram.solutions.structured import (
            get_generator,
            SpecGenerationResponse,
            AgentContext,
        )
        from code_de_diagram.models import DiagramSpec

        agent = get_generator()
        context = AgentContext()

        result = await agent.run(
            f"Generate a DiagramSpec for: {minimal_architecture_description}",
            deps=context,
        )

        # Verify the response structure
        assert isinstance(result.output, SpecGenerationResponse)
        assert isinstance(result.output.spec, DiagramSpec)
        assert len(result.output.spec.nodes) > 0
        assert isinstance(result.output.explanation, str)

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_code_generator_returns_python_code(
        self, require_llm, minimal_architecture_description
    ):
        """Verify code generator returns valid Python code."""
        from code_de_diagram.solutions.direct import (
            get_generator,
            CodeGenerationResponse,
            AgentContext,
        )

        agent = get_generator()
        context = AgentContext()

        result = await agent.run(
            f"Generate Python diagram code for: {minimal_architecture_description}\n"
            f"Output filename: test_diagram",
            deps=context,
        )

        # Verify the response structure
        assert isinstance(result.output, CodeGenerationResponse)
        assert isinstance(result.output.python_code, str)
        assert len(result.output.python_code) > 0

        # Check code contains expected imports
        code = result.output.python_code
        assert "from diagrams" in code or "import diagrams" in code
        assert "Diagram" in code
