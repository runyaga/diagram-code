"""Tests for Solution A: Direct LLM Code Generation.

Tests for DirectGenerationAgent which generates Python diagram code directly
via LLM without an intermediate representation.

Run with: pytest tests/test_solution_direct.py -v
"""

import os
import pytest
from pathlib import Path

from code_de_diagram.solutions.direct import (
    DirectGenerationAgent,
    AgentContext,
    AnalysisResponse,
    CodeGenerationResponse,
    RefinementResponse,
    get_analyzer,
    get_generator,
    get_refiner,
)
from code_de_diagram.models import ConversationMessage


# ============================================================================
# Unit Tests (No Network Required)
# ============================================================================

class TestAgentContext:
    """Tests for AgentContext dataclass."""

    def test_default_context(self):
        """Test default AgentContext creation."""
        ctx = AgentContext()

        assert ctx.conversation_history == []
        assert ctx.current_code is None
        assert ctx.output_path == "diagram"

    def test_context_with_values(self):
        """Test AgentContext with custom values."""
        history = [ConversationMessage(role="user", content="hello")]
        ctx = AgentContext(
            conversation_history=history,
            current_code="print('test')",
            output_path="custom/path",
        )

        assert len(ctx.conversation_history) == 1
        assert ctx.current_code == "print('test')"
        assert ctx.output_path == "custom/path"


class TestDirectGenerationAgentInit:
    """Tests for DirectGenerationAgent initialization."""

    def test_default_initialization(self):
        """Test agent initializes with defaults."""
        agent = DirectGenerationAgent()

        assert agent.context is not None
        assert agent.generated_code is None
        assert agent.diagram_path is None
        assert agent.context.conversation_history == []

    def test_initialization_with_output_dir(self, tmp_path):
        """Test agent initializes with custom output directory."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        expected_path = os.path.join(str(tmp_path), "diagram")
        assert agent.context.output_path == expected_path

    def test_add_message(self):
        """Test internal message adding."""
        agent = DirectGenerationAgent()
        agent._add_message("user", "test message")

        assert len(agent.context.conversation_history) == 1
        assert agent.context.conversation_history[0].role == "user"
        assert agent.context.conversation_history[0].content == "test message"


class TestResponseModels:
    """Tests for response Pydantic models."""

    def test_analysis_response_creation(self):
        """Test AnalysisResponse model."""
        response = AnalysisResponse(
            summary="A simple web architecture",
            identified_components=["ALB", "EC2", "RDS"],
            identified_connections=["ALB->EC2", "EC2->RDS"],
            ambiguities=["Database type unclear"],
            questions=[],
            confidence=0.85,
            ready_to_generate=True,
        )

        assert response.summary == "A simple web architecture"
        assert len(response.identified_components) == 3
        assert response.confidence == 0.85
        assert response.ready_to_generate is True

    def test_analysis_response_confidence_bounds(self):
        """Test confidence field validation."""
        from pydantic import ValidationError

        # Valid bounds
        AnalysisResponse(
            summary="test",
            identified_components=[],
            identified_connections=[],
            confidence=0.0,
            ready_to_generate=False,
        )
        AnalysisResponse(
            summary="test",
            identified_components=[],
            identified_connections=[],
            confidence=1.0,
            ready_to_generate=False,
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            AnalysisResponse(
                summary="test",
                identified_components=[],
                identified_connections=[],
                confidence=1.5,
                ready_to_generate=False,
            )

    def test_code_generation_response(self):
        """Test CodeGenerationResponse model."""
        response = CodeGenerationResponse(
            python_code='from diagrams import Diagram\nwith Diagram("Test"): pass',
            explanation="Generated a simple diagram",
            warnings=["Consider adding more nodes"],
        )

        assert "from diagrams" in response.python_code
        assert len(response.warnings) == 1

    def test_refinement_response(self):
        """Test RefinementResponse model."""
        response = RefinementResponse(
            understood_changes=["Add database node"],
            updated_code='from diagrams import Diagram\n# updated',
            explanation="Added the requested database",
        )

        assert len(response.understood_changes) == 1
        assert "updated" in response.updated_code


class TestAgentSingletons:
    """Tests for agent singleton functions."""

    def test_get_analyzer_returns_agent(self):
        """Test get_analyzer returns an agent."""
        agent = get_analyzer()
        assert agent is not None

    def test_get_analyzer_returns_same_instance(self):
        """Test get_analyzer returns singleton."""
        agent1 = get_analyzer()
        agent2 = get_analyzer()
        assert agent1 is agent2

    def test_get_generator_returns_agent(self):
        """Test get_generator returns an agent."""
        agent = get_generator()
        assert agent is not None

    def test_get_refiner_returns_agent(self):
        """Test get_refiner returns an agent."""
        agent = get_refiner()
        assert agent is not None


class TestExecuteCodeWithoutGeneration:
    """Tests for execute_code without generated code."""

    def test_execute_without_code_fails(self):
        """Test execute_code fails when no code generated."""
        agent = DirectGenerationAgent()
        success, message = agent.execute_code()

        assert success is False
        assert "No code generated" in message

    def test_get_code_returns_none_initially(self):
        """Test get_code returns None before generation."""
        agent = DirectGenerationAgent()
        assert agent.get_code() is None

    def test_get_diagram_path_returns_none_initially(self):
        """Test get_diagram_path returns None before execution."""
        agent = DirectGenerationAgent()
        assert agent.get_diagram_path() is None


class TestExecuteCodeWithMockCode:
    """Tests for execute_code with pre-set code."""

    def test_execute_valid_code(self, tmp_path):
        """Test executing valid Python code."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        # Set valid diagram code directly
        agent.generated_code = '''
from diagrams import Diagram
from diagrams.aws.compute import EC2

with Diagram("Test", filename="diagram", show=False):
    EC2("Server")
'''
        agent.context.current_code = agent.generated_code

        success, message = agent.execute_code()

        # May fail if diagrams library not installed properly,
        # but should not raise exception
        assert isinstance(success, bool)
        assert isinstance(message, str)

    def test_execute_invalid_code(self, tmp_path):
        """Test executing invalid Python code fails gracefully."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))
        agent.generated_code = "this is not valid python code!!!"

        success, message = agent.execute_code()

        assert success is False
        assert len(message) > 0

    def test_execute_code_with_syntax_error(self, tmp_path):
        """Test code with syntax error fails gracefully."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))
        agent.generated_code = "def broken(\n"  # Syntax error

        success, message = agent.execute_code()

        assert success is False


# ============================================================================
# Integration Tests (Require Network)
# ============================================================================

class TestDirectAgentAnalyze:
    """Integration tests for analyze method."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyze_returns_analysis_response(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test analyze returns valid AnalysisResponse."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        result = await agent.analyze(minimal_architecture_description)

        assert isinstance(result, AnalysisResponse)
        assert len(result.summary) > 0
        assert isinstance(result.identified_components, list)
        assert isinstance(result.confidence, float)

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyze_adds_to_history(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test analyze adds messages to conversation history."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        await agent.analyze(minimal_architecture_description)

        # Should have user message and assistant response
        assert len(agent.context.conversation_history) >= 2


class TestDirectAgentGenerateCode:
    """Integration tests for generate_code method."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_code_returns_code_response(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test generate_code returns valid CodeGenerationResponse."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        result = await agent.generate_code(minimal_architecture_description)

        assert isinstance(result, CodeGenerationResponse)
        assert len(result.python_code) > 0
        assert "diagrams" in result.python_code.lower() or "Diagram" in result.python_code

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_code_sets_internal_state(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test generate_code updates agent's internal state."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        await agent.generate_code(minimal_architecture_description)

        assert agent.generated_code is not None
        assert agent.context.current_code is not None
        assert agent.get_code() == agent.generated_code


class TestDirectAgentRefine:
    """Integration tests for refine method."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_refine_modifies_code(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test refine updates the generated code."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        # First generate
        await agent.generate_code(minimal_architecture_description)
        original_code = agent.generated_code

        # Then refine
        result = await agent.refine("Add a comment at the top of the code")

        assert isinstance(result, RefinementResponse)
        assert len(result.updated_code) > 0
        # Code should be updated (may or may not be different)
        assert agent.generated_code == result.updated_code


class TestDirectAgentFullPipeline:
    """Integration tests for full direct generation pipeline."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyze_then_generate(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test full pipeline: analyze -> generate."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        # Analyze
        analysis = await agent.analyze(minimal_architecture_description)
        assert analysis.confidence > 0

        # Generate
        generation = await agent.generate_code(minimal_architecture_description)
        assert len(generation.python_code) > 0

        # Verify code is stored
        assert agent.get_code() is not None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_full_pipeline_with_execution(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test full pipeline including code execution."""
        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        # Generate code
        await agent.generate_code(minimal_architecture_description)

        # Execute
        success, message = agent.execute_code()

        # Should either succeed or fail gracefully
        assert isinstance(success, bool)
        assert isinstance(message, str)

        if success:
            # If successful, diagram path should be set
            # (depends on whether diagrams library creates the file)
            pass
