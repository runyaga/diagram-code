"""code.de.diagram - LLM-driven architecture diagram generation."""

from .models import (
    NodeType,
    EdgeStyle,
    DiagramNode,
    DiagramEdge,
    DiagramCluster,
    DiagramSpec,
    ClarifyingQuestion,
    ConversationMessage,
)

from .config import (
    ModelProvider,
    get_model_name,
    get_ollama_base_url,
    print_config,
)

from .renderer import (
    DiagramRenderer,
    render_spec_to_code,
    render_and_execute,
)

from .spec_parser import (
    parse_spec_file,
    spec_to_natural_language,
    get_expected_counts,
)

from .vlm_verifier import (
    analyze_diagram,
    verify_diagram,
    full_verification,
    DiagramAnalysis,
    VerificationResult,
)

from .solutions import (
    DirectGenerationAgent,
    StructuredAgent,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Models
    "NodeType",
    "EdgeStyle",
    "DiagramNode",
    "DiagramEdge",
    "DiagramCluster",
    "DiagramSpec",
    "ClarifyingQuestion",
    "ConversationMessage",
    # Config
    "ModelProvider",
    "get_model_name",
    "get_ollama_base_url",
    "print_config",
    # Renderer
    "DiagramRenderer",
    "render_spec_to_code",
    "render_and_execute",
    # Spec Parser
    "parse_spec_file",
    "spec_to_natural_language",
    "get_expected_counts",
    # VLM Verifier
    "analyze_diagram",
    "verify_diagram",
    "full_verification",
    "DiagramAnalysis",
    "VerificationResult",
    # Agents
    "DirectGenerationAgent",
    "StructuredAgent",
]
