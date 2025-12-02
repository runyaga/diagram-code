"""End-to-end integration tests for the diagram-as-code pipeline.

These tests verify the complete pipeline from SPEC.md to generated diagram,
including both solutions and VLM verification.

Run with: pytest tests/test_e2e.py -v -m integration
"""

import os
import pytest
from pathlib import Path

from code_de_diagram.models import DiagramSpec
from code_de_diagram.spec_parser import parse_spec_file, spec_to_natural_language
from code_de_diagram.renderer import render_spec_to_code, render_and_execute


# ============================================================================
# Spec Parsing Tests
# ============================================================================

class TestSpecParsing:
    """Tests for parsing SPEC.md files."""

    def test_parse_example_spec(self, example_spec_path):
        """Test parsing the example SPEC.md file."""
        spec = parse_spec_file(example_spec_path)

        assert isinstance(spec, DiagramSpec)
        assert len(spec.name) > 0
        assert len(spec.nodes) > 0
        assert len(spec.edges) > 0

    def test_spec_to_natural_language(self, example_spec_path):
        """Test converting spec to natural language."""
        spec = parse_spec_file(example_spec_path)
        nl = spec_to_natural_language(spec)

        assert isinstance(nl, str)
        assert len(nl) > 0
        assert spec.name in nl


# ============================================================================
# Renderer Execution Tests
# ============================================================================

class TestRendererExecution:
    """Tests for renderer code execution."""

    def test_render_and_execute_simple_spec(self, simple_spec, tmp_path):
        """Test rendering and executing a simple spec."""
        output_path = str(tmp_path / "test_diagram")

        success, message, code = render_and_execute(simple_spec, output_path)

        assert isinstance(success, bool)
        assert isinstance(message, str)
        assert isinstance(code, str)

        # Code should be valid Python
        assert "from diagrams" in code
        assert "Diagram" in code

    def test_render_creates_png(self, minimal_spec, tmp_path):
        """Test that successful render creates a PNG file."""
        output_path = str(tmp_path / "diagram")

        success, message, code = render_and_execute(minimal_spec, output_path)

        if success:
            png_path = Path(f"{output_path}.png")
            assert png_path.exists(), f"PNG not created at {png_path}"

            # Verify it's a valid PNG (check magic bytes)
            with open(png_path, "rb") as f:
                header = f.read(8)
                # PNG signature
                assert header[:4] == b'\x89PNG', "File is not a valid PNG"


# ============================================================================
# Direct Solution E2E Tests
# ============================================================================

class TestDirectSolutionE2E:
    """End-to-end tests for Solution A (Direct)."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_direct_from_spec_file(
        self, require_llm, example_spec_path, tmp_path
    ):
        """Test direct generation from a SPEC.md file."""
        from code_de_diagram.solutions.direct import DirectGenerationAgent

        # Parse spec and convert to natural language
        spec = parse_spec_file(example_spec_path)
        description = spec_to_natural_language(spec)

        # Create agent and generate
        agent = DirectGenerationAgent(output_dir=str(tmp_path))
        result = await agent.generate_code(description)

        assert result.python_code is not None
        assert len(result.python_code) > 0
        assert "diagrams" in result.python_code.lower()

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_direct_produces_executable_code(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test direct generation produces code that can be executed."""
        from code_de_diagram.solutions.direct import DirectGenerationAgent

        agent = DirectGenerationAgent(output_dir=str(tmp_path))

        # Generate code
        result = await agent.generate_code(minimal_architecture_description)

        # Attempt to execute
        success, message = agent.execute_code()

        # We expect it to at least not crash
        # Success depends on the quality of generated code
        assert isinstance(success, bool)
        assert isinstance(message, str)


# ============================================================================
# Structured Solution E2E Tests
# ============================================================================

class TestStructuredSolutionE2E:
    """End-to-end tests for Solution B (Structured)."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_structured_from_spec_file(
        self, require_llm, example_spec_path, tmp_path
    ):
        """Test structured generation from a SPEC.md file."""
        from code_de_diagram.solutions.structured import StructuredAgent

        # Parse spec and convert to natural language
        spec = parse_spec_file(example_spec_path)
        description = spec_to_natural_language(spec)

        # Create agent and generate
        agent = StructuredAgent(output_dir=str(tmp_path))
        result = await agent.generate_spec(description)

        assert result.spec is not None
        assert len(result.spec.nodes) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_structured_produces_diagram(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test structured generation produces a diagram file."""
        from code_de_diagram.solutions.structured import StructuredAgent

        agent = StructuredAgent(output_dir=str(tmp_path))

        # Generate spec
        await agent.generate_spec(minimal_architecture_description)

        # Execute to produce diagram
        success, message = agent.execute()

        if success:
            diagram_path = agent.get_diagram_path()
            assert diagram_path is not None
            assert Path(diagram_path).exists()

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_structured_spec_matches_input(
        self, require_llm, tmp_path
    ):
        """Test structured spec contains expected components."""
        from code_de_diagram.solutions.structured import StructuredAgent

        description = """
        A simple architecture with:
        - One Application Load Balancer named "Main ALB"
        - One EC2 instance named "Web Server"
        - One RDS database named "Primary DB"
        - ALB connects to EC2, EC2 connects to RDS
        """

        agent = StructuredAgent(output_dir=str(tmp_path))
        result = await agent.generate_spec(description)

        # Should have 3 nodes
        assert len(result.spec.nodes) >= 3

        # Should have at least 2 edges
        assert len(result.spec.edges) >= 2

        # Check that expected node types are present
        node_types = [n.node_type.value for n in result.spec.nodes]
        # At least some AWS components should be identified
        assert any(t in ["alb", "ec2", "rds"] for t in node_types)


# ============================================================================
# Full Pipeline with VLM Verification Tests
# ============================================================================

class TestFullPipelineWithVLM:
    """End-to-end tests including VLM verification."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_structured_with_vlm_verification(
        self, require_llm, require_vlm, minimal_architecture_description, tmp_path
    ):
        """Test full pipeline: generate spec -> render -> execute -> verify."""
        from code_de_diagram.solutions.structured import StructuredAgent
        from code_de_diagram.vlm_verifier import full_verification

        agent = StructuredAgent(output_dir=str(tmp_path))

        # Generate spec
        result = await agent.generate_spec(minimal_architecture_description)
        spec = result.spec

        # Execute to produce diagram
        success, message = agent.execute()

        if success:
            diagram_path = agent.get_diagram_path()
            assert Path(diagram_path).exists()

            # Run VLM verification
            verification = await full_verification(diagram_path, spec)

            assert verification["error"] is None
            assert verification["analysis"] is not None
            assert verification["verification"] is not None
            assert 0.0 <= verification["verification"]["accuracy_score"] <= 1.0


# ============================================================================
# Comparison Tests
# ============================================================================

class TestSolutionComparison:
    """Tests comparing both solutions."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_both_solutions_produce_code(
        self, require_llm, minimal_architecture_description, tmp_path
    ):
        """Test both solutions can produce code for the same input."""
        from code_de_diagram.solutions.direct import DirectGenerationAgent
        from code_de_diagram.solutions.structured import StructuredAgent

        # Direct solution
        direct_agent = DirectGenerationAgent(output_dir=str(tmp_path / "direct"))
        direct_result = await direct_agent.generate_code(minimal_architecture_description)

        # Structured solution
        structured_agent = StructuredAgent(output_dir=str(tmp_path / "structured"))
        await structured_agent.generate_spec(minimal_architecture_description)
        structured_code = structured_agent.render_code()

        # Both should produce code
        assert len(direct_result.python_code) > 0
        assert len(structured_code) > 0

        # Both should import diagrams
        assert "diagrams" in direct_result.python_code.lower()
        assert "diagrams" in structured_code.lower()


# ============================================================================
# CLI Function Tests
# ============================================================================

class TestCLIFunctions:
    """Tests for CLI utility functions."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_run_from_spec_structured(
        self, require_llm, example_spec_path, tmp_path
    ):
        """Test run_from_spec function with structured solution."""
        from code_de_diagram.cli import run_from_spec

        results = await run_from_spec(
            spec_path=str(example_spec_path),
            output_dir=str(tmp_path),
            solution="structured",
        )

        assert isinstance(results, dict)
        assert "ground_truth" in results
        assert "generated" in results
        assert "success" in results

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_run_from_spec_direct(
        self, require_llm, example_spec_path, tmp_path
    ):
        """Test run_from_spec function with direct solution."""
        from code_de_diagram.cli import run_from_spec

        results = await run_from_spec(
            spec_path=str(example_spec_path),
            output_dir=str(tmp_path),
            solution="direct",
        )

        assert isinstance(results, dict)
        assert "success" in results


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in the pipeline."""

    def test_parse_nonexistent_spec(self, tmp_path):
        """Test parsing non-existent spec file raises error."""
        with pytest.raises(FileNotFoundError):
            parse_spec_file(tmp_path / "nonexistent.md")

    def test_render_empty_spec(self, tmp_path):
        """Test rendering empty spec produces minimal code."""
        spec = DiagramSpec(name="Empty")
        code = render_spec_to_code(spec, str(tmp_path / "empty"))

        assert "from diagrams" in code
        assert "Empty" in code

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_handles_empty_input(self, require_llm, tmp_path):
        """Test agents handle empty input gracefully."""
        from code_de_diagram.solutions.structured import StructuredAgent

        agent = StructuredAgent(output_dir=str(tmp_path))

        # Empty input should still work (though results may be minimal)
        result = await agent.analyze("")

        assert result is not None
        assert isinstance(result.summary, str)


# ============================================================================
# Performance Smoke Tests
# ============================================================================

class TestPerformance:
    """Basic performance tests."""

    def test_render_speed(self, simple_spec, tmp_path):
        """Test rendering completes in reasonable time."""
        import time

        start = time.time()
        code = render_spec_to_code(simple_spec, str(tmp_path / "test"))
        elapsed = time.time() - start

        # Rendering should be fast (under 1 second)
        assert elapsed < 1.0
        assert len(code) > 0

    def test_spec_parsing_speed(self, example_spec_path):
        """Test spec parsing completes in reasonable time."""
        import time

        start = time.time()
        spec = parse_spec_file(example_spec_path)
        elapsed = time.time() - start

        # Parsing should be fast (under 1 second)
        assert elapsed < 1.0
        assert spec is not None
