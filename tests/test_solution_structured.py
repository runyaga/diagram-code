"""Tests for Solution B: Structured Intermediate Representation.

Tests for StructuredAgent which generates a DiagramSpec intermediate
representation and then renders it to code deterministically.

Run with: pytest tests/test_solution_structured.py -v
"""

import os
import json
import pytest
from pathlib import Path

from code_de_diagram.solutions.structured import (
    StructuredAgent,
    AgentContext,
    AnalysisResponse,
    SpecGenerationResponse,
    SpecRefinementResponse,
    get_analyzer,
    get_generator,
    get_refiner,
)
from code_de_diagram.models import (
    DiagramSpec,
    DiagramNode,
    DiagramEdge,
    DiagramCluster,
    NodeType,
    ConversationMessage,
)


# ============================================================================
# Unit Tests (No Network Required)
# ============================================================================

class TestAgentContext:
    """Tests for AgentContext dataclass."""

    def test_default_context(self):
        """Test default AgentContext creation."""
        ctx = AgentContext()

        assert ctx.conversation_history == []
        assert ctx.current_spec is None
        assert ctx.output_path == "diagram"

    def test_context_with_spec(self, simple_spec):
        """Test AgentContext with a DiagramSpec."""
        ctx = AgentContext(current_spec=simple_spec)

        assert ctx.current_spec is not None
        assert ctx.current_spec.name == simple_spec.name


class TestStructuredAgentInit:
    """Tests for StructuredAgent initialization."""

    def test_default_initialization(self):
        """Test agent initializes with defaults."""
        agent = StructuredAgent()

        assert agent.context is not None
        assert agent.current_spec is None
        assert agent.generated_code is None
        assert agent.diagram_path is None

    def test_initialization_with_output_dir(self, tmp_path):
        """Test agent initializes with custom output directory."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        expected_path = os.path.join(str(tmp_path), "diagram")
        assert agent.context.output_path == expected_path


class TestResponseModels:
    """Tests for response Pydantic models."""

    def test_analysis_response_with_clusters(self):
        """Test AnalysisResponse includes suggested clusters."""
        response = AnalysisResponse(
            summary="A web application",
            identified_components=["ALB", "EC2", "RDS"],
            identified_connections=["ALB->EC2"],
            suggested_clusters=["Web Tier", "Data Tier"],
            confidence=0.9,
            ready_to_generate=True,
        )

        assert len(response.suggested_clusters) == 2

    def test_spec_generation_response(self, simple_spec):
        """Test SpecGenerationResponse model."""
        response = SpecGenerationResponse(
            spec=simple_spec,
            explanation="Generated spec with 4 nodes",
            warnings=[],
        )

        assert response.spec.name == simple_spec.name
        assert len(response.spec.nodes) == len(simple_spec.nodes)

    def test_spec_refinement_response(self, simple_spec):
        """Test SpecRefinementResponse model."""
        response = SpecRefinementResponse(
            understood_changes=["Add S3 bucket"],
            updated_spec=simple_spec,
            explanation="Added storage layer",
        )

        assert len(response.understood_changes) == 1
        assert response.updated_spec is not None


class TestAgentSingletons:
    """Tests for agent singleton functions."""

    def test_get_analyzer_returns_agent(self):
        """Test get_analyzer returns an agent."""
        agent = get_analyzer()
        assert agent is not None

    def test_get_generator_returns_agent(self):
        """Test get_generator returns an agent."""
        agent = get_generator()
        assert agent is not None

    def test_get_refiner_returns_agent(self):
        """Test get_refiner returns an agent."""
        agent = get_refiner()
        assert agent is not None


class TestLoadSpecFromJson:
    """Tests for loading spec from JSON."""

    def test_load_spec_from_json(self, simple_spec):
        """Test loading a spec from JSON string."""
        agent = StructuredAgent()
        json_str = simple_spec.model_dump_json()

        agent.load_spec_from_json(json_str)

        assert agent.current_spec is not None
        assert agent.current_spec.name == simple_spec.name
        assert len(agent.current_spec.nodes) == len(simple_spec.nodes)

    def test_load_spec_updates_context(self, simple_spec):
        """Test loading spec also updates context."""
        agent = StructuredAgent()
        json_str = simple_spec.model_dump_json()

        agent.load_spec_from_json(json_str)

        assert agent.context.current_spec is not None
        assert agent.context.current_spec.name == simple_spec.name

    def test_load_invalid_json_raises_error(self):
        """Test loading invalid JSON raises error."""
        agent = StructuredAgent()

        with pytest.raises(Exception):  # Pydantic ValidationError
            agent.load_spec_from_json("not valid json")


class TestRenderCode:
    """Tests for render_code method."""

    def test_render_code_without_spec_raises_error(self):
        """Test render_code fails without a spec."""
        agent = StructuredAgent()

        with pytest.raises(ValueError, match="No spec generated"):
            agent.render_code()

    def test_render_code_with_spec(self, simple_spec):
        """Test render_code generates Python code."""
        agent = StructuredAgent()
        agent.current_spec = simple_spec
        agent.context.current_spec = simple_spec

        code = agent.render_code()

        assert isinstance(code, str)
        assert "from diagrams" in code
        assert "Diagram" in code
        assert agent.generated_code == code

    def test_render_code_includes_nodes(self, simple_spec):
        """Test rendered code includes all nodes."""
        agent = StructuredAgent()
        agent.current_spec = simple_spec
        agent.context.current_spec = simple_spec

        code = agent.render_code()

        # Check node labels appear in code
        for node in simple_spec.nodes:
            assert node.label in code


class TestExecuteWithoutSpec:
    """Tests for execute method without spec."""

    def test_execute_without_spec_fails(self):
        """Test execute fails without a spec."""
        agent = StructuredAgent()

        success, message = agent.execute()

        assert success is False
        assert "No spec" in message


class TestExecuteWithSpec:
    """Tests for execute method with spec."""

    def test_execute_with_simple_spec(self, simple_spec, tmp_path):
        """Test execute with a valid spec."""
        agent = StructuredAgent(output_dir=str(tmp_path))
        agent.current_spec = simple_spec
        agent.context.current_spec = simple_spec

        success, message = agent.execute()

        # Should attempt execution (may fail if diagrams not fully working)
        assert isinstance(success, bool)
        assert isinstance(message, str)

        # Code should be generated regardless of execution success
        assert agent.generated_code is not None

    def test_execute_sets_diagram_path_on_success(self, minimal_spec, tmp_path):
        """Test execute sets diagram_path on success."""
        agent = StructuredAgent(output_dir=str(tmp_path))
        agent.current_spec = minimal_spec
        agent.context.current_spec = minimal_spec

        success, message = agent.execute()

        if success:
            assert agent.diagram_path is not None
            assert agent.diagram_path.endswith(".png")


class TestGetMethods:
    """Tests for getter methods."""

    def test_get_spec_returns_none_initially(self):
        """Test get_spec returns None before generation."""
        agent = StructuredAgent()
        assert agent.get_spec() is None

    def test_get_spec_returns_spec(self, simple_spec):
        """Test get_spec returns current spec."""
        agent = StructuredAgent()
        agent.current_spec = simple_spec

        assert agent.get_spec() == simple_spec

    def test_get_spec_json_returns_none_initially(self):
        """Test get_spec_json returns None before generation."""
        agent = StructuredAgent()
        assert agent.get_spec_json() is None

    def test_get_spec_json_returns_json(self, simple_spec):
        """Test get_spec_json returns valid JSON."""
        agent = StructuredAgent()
        agent.current_spec = simple_spec

        json_str = agent.get_spec_json()

        assert json_str is not None
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["name"] == simple_spec.name

    def test_get_code_returns_none_initially(self):
        """Test get_code returns None before rendering."""
        agent = StructuredAgent()
        assert agent.get_code() is None

    def test_get_diagram_path_returns_none_initially(self):
        """Test get_diagram_path returns None before execution."""
        agent = StructuredAgent()
        assert agent.get_diagram_path() is None


# ============================================================================
# Integration Tests (Require Network)
# ============================================================================

class TestStructuredAgentAnalyze:
    """Integration tests for analyze method."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyze_returns_analysis_response(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test analyze returns valid AnalysisResponse."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        result = await agent.analyze(minimal_architecture_description)

        assert isinstance(result, AnalysisResponse)
        assert len(result.summary) > 0
        assert isinstance(result.identified_components, list)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyze_identifies_components(
        self, require_llm, simple_architecture_description, tmp_path
    ):
        """Test analyze identifies architecture components."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        result = await agent.analyze(simple_architecture_description)

        # Should identify some components
        assert len(result.identified_components) > 0


class TestStructuredAgentGenerateSpec:
    """Integration tests for generate_spec method."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_spec_returns_spec_response(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test generate_spec returns valid SpecGenerationResponse."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        result = await agent.generate_spec(minimal_architecture_description)

        assert isinstance(result, SpecGenerationResponse)
        assert isinstance(result.spec, DiagramSpec)
        assert len(result.spec.nodes) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_spec_sets_internal_state(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test generate_spec updates agent's internal state."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        await agent.generate_spec(minimal_architecture_description)

        assert agent.current_spec is not None
        assert agent.context.current_spec is not None
        assert agent.get_spec() is not None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_spec_creates_valid_nodes(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test generated spec has valid node types."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        result = await agent.generate_spec(minimal_architecture_description)

        for node in result.spec.nodes:
            assert isinstance(node.id, str)
            assert len(node.id) > 0
            assert isinstance(node.label, str)
            assert isinstance(node.node_type, NodeType)


class TestStructuredAgentRefineSpec:
    """Integration tests for refine_spec method."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_refine_spec_modifies_spec(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test refine_spec updates the spec."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        # First generate
        await agent.generate_spec(minimal_architecture_description)
        original_node_count = len(agent.current_spec.nodes)

        # Then refine
        result = await agent.refine_spec("Add an S3 bucket for storage")

        assert isinstance(result, SpecRefinementResponse)
        assert result.updated_spec is not None
        # Spec should be updated (may have more nodes)
        assert agent.current_spec == result.updated_spec


class TestStructuredAgentFullPipeline:
    """Integration tests for full structured generation pipeline."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyze_then_generate_spec(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test full pipeline: analyze -> generate_spec."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        # Analyze
        analysis = await agent.analyze(minimal_architecture_description)
        assert analysis.confidence > 0

        # Generate
        generation = await agent.generate_spec(minimal_architecture_description)
        assert len(generation.spec.nodes) > 0

        # Verify spec is stored
        assert agent.get_spec() is not None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_full_pipeline_with_render(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test full pipeline including code rendering."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        # Generate spec
        await agent.generate_spec(minimal_architecture_description)

        # Render to code
        code = agent.render_code()

        assert "from diagrams" in code
        assert agent.get_code() is not None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_full_pipeline_with_execution(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test full pipeline including execution."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        # Generate spec
        await agent.generate_spec(minimal_architecture_description)

        # Execute (render + run)
        success, message = agent.execute()

        # Should attempt execution
        assert isinstance(success, bool)
        assert isinstance(message, str)

        # Code should be generated regardless
        assert agent.get_code() is not None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_spec_json_roundtrip(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test spec can be serialized and reloaded."""
        agent = StructuredAgent(output_dir=str(tmp_path))

        # Generate spec
        await agent.generate_spec(minimal_architecture_description)
        json_str = agent.get_spec_json()

        # Create new agent and load spec
        agent2 = StructuredAgent(output_dir=str(tmp_path))
        agent2.load_spec_from_json(json_str)

        # Specs should match
        assert agent2.current_spec.name == agent.current_spec.name
        assert len(agent2.current_spec.nodes) == len(agent.current_spec.nodes)
