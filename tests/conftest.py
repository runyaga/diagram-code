"""Shared fixtures for tests."""

import os
import pytest
import asyncio
from pathlib import Path
from typing import Optional

from code_de_diagram.models import (
    NodeType,
    DiagramNode,
    DiagramEdge,
    DiagramCluster,
    DiagramSpec,
)
from code_de_diagram.config import ModelProvider, get_ollama_base_url


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require external services)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


# ============================================================================
# Environment Detection Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def ollama_available() -> bool:
    """Check if Ollama server is available."""
    import httpx

    base_url = get_ollama_base_url().replace("/v1", "")
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def openai_available() -> bool:
    """Check if OpenAI API key is configured."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    return api_key.startswith("sk-") and len(api_key) > 20


@pytest.fixture(scope="session")
def current_provider() -> ModelProvider:
    """Get the current model provider from environment."""
    return ModelProvider.from_env()


# ============================================================================
# Skip Condition Fixtures
# ============================================================================

@pytest.fixture
def require_ollama(ollama_available):
    """Skip test if Ollama is not available."""
    if not ollama_available:
        pytest.skip("Ollama server not available")


@pytest.fixture
def require_openai(openai_available):
    """Skip test if OpenAI is not configured."""
    if not openai_available:
        pytest.skip("OpenAI API key not configured")


@pytest.fixture
def require_llm(ollama_available, openai_available, current_provider):
    """Skip test if no LLM provider is available."""
    if current_provider == ModelProvider.OLLAMA and not ollama_available:
        pytest.skip("Ollama server not available")
    if current_provider == ModelProvider.OPENAI and not openai_available:
        pytest.skip("OpenAI API key not configured")


@pytest.fixture
def require_vlm(ollama_available, openai_available, current_provider):
    """Skip test if no VLM provider is available."""
    # VLM uses same providers as LLM
    if current_provider == ModelProvider.OLLAMA and not ollama_available:
        pytest.skip("Ollama server not available for VLM")
    if current_provider == ModelProvider.OPENAI and not openai_available:
        pytest.skip("OpenAI API key not configured for VLM")


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def example_dir(project_root) -> Path:
    """Get the example directory."""
    return project_root / "example"


@pytest.fixture(scope="session")
def example_spec_path(example_dir) -> Path:
    """Get the path to the example SPEC.md file."""
    spec_path = example_dir / "SPEC.md"
    if not spec_path.exists():
        pytest.skip("Example SPEC.md not found")
    return spec_path


@pytest.fixture(scope="session")
def example_diagram_path(example_dir) -> Path:
    """Get the path to the example diagram PNG."""
    diagram_path = example_dir / "aws-diagram.png"
    if not diagram_path.exists():
        pytest.skip("Example aws-diagram.png not found")
    return diagram_path


# ============================================================================
# DiagramSpec Fixtures
# ============================================================================

@pytest.fixture
def simple_spec() -> DiagramSpec:
    """Create a simple DiagramSpec for testing."""
    return DiagramSpec(
        name="Simple Test Architecture",
        description="A simple web application architecture",
        direction="TB",
        nodes=[
            DiagramNode(id="alb", label="Load Balancer", node_type=NodeType.ALB),
            DiagramNode(id="web1", label="Web Server 1", node_type=NodeType.EC2),
            DiagramNode(id="web2", label="Web Server 2", node_type=NodeType.EC2),
            DiagramNode(id="db", label="Database", node_type=NodeType.RDS),
        ],
        edges=[
            DiagramEdge(source="alb", target="web1", label="HTTP"),
            DiagramEdge(source="alb", target="web2", label="HTTP"),
            DiagramEdge(source="web1", target="db", label="TCP/5432"),
            DiagramEdge(source="web2", target="db", label="TCP/5432"),
        ],
        clusters=[
            DiagramCluster(id="web_tier", label="Web Tier", node_ids=["web1", "web2"]),
        ],
    )


@pytest.fixture
def minimal_spec() -> DiagramSpec:
    """Create a minimal DiagramSpec for quick tests."""
    return DiagramSpec(
        name="Minimal Test",
        nodes=[
            DiagramNode(id="a", label="Service A", node_type=NodeType.EC2),
            DiagramNode(id="b", label="Service B", node_type=NodeType.RDS),
        ],
        edges=[
            DiagramEdge(source="a", target="b"),
        ],
    )


@pytest.fixture
def simple_architecture_description() -> str:
    """A simple architecture description for LLM tests."""
    return """
    Create a simple web application architecture with:
    - An Application Load Balancer as the entry point
    - Two EC2 web servers behind the load balancer
    - A single RDS PostgreSQL database
    - The web servers should be in a "Web Tier" cluster
    - Connections from ALB to both web servers
    - Connections from both web servers to the database
    """


@pytest.fixture
def minimal_architecture_description() -> str:
    """A minimal architecture description for quick smoke tests."""
    return "A single EC2 instance connecting to an RDS database."


# ============================================================================
# Async Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Temporary Output Directory Fixture
# ============================================================================

@pytest.fixture
def output_dir(tmp_path) -> Path:
    """Create a temporary output directory for tests."""
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    return output
