"""Integration tests for VLM (Vision Language Model) functionality.

These tests verify that the VLM can analyze diagram images and
verify them against specifications.

Run with: pytest tests/test_integration_vlm.py -v -m integration
"""

import pytest
from pathlib import Path

from code_de_diagram.models import DiagramSpec, DiagramNode, DiagramEdge, NodeType
from code_de_diagram.vlm_verifier import (
    DiagramAnalysis,
    VerificationResult,
    get_vlm_model_info,
    _encode_image,
    _spec_to_checklist,
)


# ============================================================================
# Unit Tests for VLM Helper Functions (No Network Required)
# ============================================================================

class TestVLMHelpers:
    """Unit tests for VLM helper functions that don't require network."""

    def test_encode_image(self, example_diagram_path):
        """Test image encoding to base64."""
        encoded = _encode_image(str(example_diagram_path))

        assert isinstance(encoded, str)
        assert len(encoded) > 100  # Should be a substantial string
        # Base64 encoded data should only contain valid characters
        import base64
        try:
            decoded = base64.b64decode(encoded)
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"Invalid base64 encoding: {e}")

    def test_encode_image_file_not_found(self, tmp_path):
        """Test encoding non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            _encode_image(str(tmp_path / "nonexistent.png"))

    def test_spec_to_checklist_basic(self, simple_spec):
        """Test converting a spec to verification checklist."""
        checklist = _spec_to_checklist(simple_spec)

        assert isinstance(checklist, str)
        assert simple_spec.name in checklist
        assert "Expected Nodes:" in checklist
        assert "Expected Edges:" in checklist
        assert "Expected Clusters:" in checklist

        # Check nodes are listed
        for node in simple_spec.nodes:
            assert node.label in checklist

    def test_spec_to_checklist_empty_spec(self):
        """Test checklist generation with empty spec."""
        spec = DiagramSpec(name="Empty Test")
        checklist = _spec_to_checklist(spec)

        assert "Empty Test" in checklist
        assert "Expected Nodes:" in checklist

    def test_spec_to_checklist_with_edge_labels(self):
        """Test checklist includes edge labels."""
        spec = DiagramSpec(
            name="Test",
            nodes=[
                DiagramNode(id="a", label="Service A", node_type=NodeType.EC2),
                DiagramNode(id="b", label="Service B", node_type=NodeType.RDS),
            ],
            edges=[
                DiagramEdge(source="a", target="b", label="TCP/5432"),
            ],
        )
        checklist = _spec_to_checklist(spec)

        assert "TCP/5432" in checklist
        assert "Service A -> Service B" in checklist

    def test_get_vlm_model_info(self):
        """Test VLM model info retrieval."""
        info = get_vlm_model_info()

        assert isinstance(info, dict)
        assert "provider" in info
        assert "model" in info
        assert "full_name" in info
        assert info["provider"] in ["openai", "ollama"]


# ============================================================================
# DiagramAnalysis Model Tests
# ============================================================================

class TestDiagramAnalysisModel:
    """Tests for DiagramAnalysis Pydantic model."""

    def test_create_diagram_analysis(self):
        """Test creating a DiagramAnalysis instance."""
        analysis = DiagramAnalysis(
            identified_components=["ALB", "EC2", "RDS"],
            identified_connections=["ALB -> EC2", "EC2 -> RDS"],
            identified_clusters=["Web Tier"],
            diagram_title="Test Architecture",
            overall_description="A simple web application",
        )

        assert len(analysis.identified_components) == 3
        assert len(analysis.identified_connections) == 2
        assert analysis.diagram_title == "Test Architecture"

    def test_diagram_analysis_optional_title(self):
        """Test DiagramAnalysis with optional fields."""
        analysis = DiagramAnalysis(
            identified_components=["A"],
            identified_connections=[],
            identified_clusters=[],
            overall_description="Test",
        )

        assert analysis.diagram_title is None

    def test_diagram_analysis_serialization(self):
        """Test DiagramAnalysis JSON serialization."""
        analysis = DiagramAnalysis(
            identified_components=["EC2"],
            identified_connections=["A -> B"],
            identified_clusters=["VPC"],
            overall_description="Test diagram",
        )

        json_str = analysis.model_dump_json()
        loaded = DiagramAnalysis.model_validate_json(json_str)

        assert loaded.identified_components == analysis.identified_components


# ============================================================================
# VerificationResult Model Tests
# ============================================================================

class TestVerificationResultModel:
    """Tests for VerificationResult Pydantic model."""

    def test_create_verification_result(self):
        """Test creating a VerificationResult instance."""
        result = VerificationResult(
            node_matches=["ALB", "EC2"],
            node_missing=["RDS"],
            node_extra=["Lambda"],
            edge_matches=["ALB -> EC2"],
            edge_missing=["EC2 -> RDS"],
            cluster_matches=["VPC"],
            cluster_missing=[],
            accuracy_score=0.75,
            issues=["Missing database node"],
        )

        assert len(result.node_matches) == 2
        assert result.accuracy_score == 0.75
        assert len(result.issues) == 1

    def test_verification_result_accuracy_bounds(self):
        """Test accuracy score validation bounds."""
        # Valid bounds
        result = VerificationResult(
            node_matches=[],
            node_missing=[],
            node_extra=[],
            edge_matches=[],
            edge_missing=[],
            cluster_matches=[],
            cluster_missing=[],
            accuracy_score=0.0,
        )
        assert result.accuracy_score == 0.0

        result = VerificationResult(
            node_matches=[],
            node_missing=[],
            node_extra=[],
            edge_matches=[],
            edge_missing=[],
            cluster_matches=[],
            cluster_missing=[],
            accuracy_score=1.0,
        )
        assert result.accuracy_score == 1.0

    def test_verification_result_accuracy_invalid(self):
        """Test accuracy score rejects invalid values."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            VerificationResult(
                node_matches=[],
                node_missing=[],
                node_extra=[],
                edge_matches=[],
                edge_missing=[],
                cluster_matches=[],
                cluster_missing=[],
                accuracy_score=1.5,  # Invalid: > 1.0
            )

    def test_verification_result_default_issues(self):
        """Test issues field defaults to empty list."""
        result = VerificationResult(
            node_matches=[],
            node_missing=[],
            node_extra=[],
            edge_matches=[],
            edge_missing=[],
            cluster_matches=[],
            cluster_missing=[],
            accuracy_score=0.5,
        )
        assert result.issues == []


# ============================================================================
# VLM Integration Tests (Require Network)
# ============================================================================

class TestVLMAnalysis:
    """Integration tests for VLM diagram analysis."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_analyze_diagram_returns_analysis(
        self, require_vlm, example_diagram_path
    ):
        """Test that analyze_diagram returns valid DiagramAnalysis."""
        from code_de_diagram.vlm_verifier import analyze_diagram

        analysis = await analyze_diagram(str(example_diagram_path))

        assert isinstance(analysis, DiagramAnalysis)
        assert isinstance(analysis.identified_components, list)
        assert isinstance(analysis.identified_connections, list)
        assert isinstance(analysis.identified_clusters, list)
        assert isinstance(analysis.overall_description, str)
        assert len(analysis.overall_description) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_diagram_file_not_found(self, require_vlm, tmp_path):
        """Test analyze_diagram raises error for missing file."""
        from code_de_diagram.vlm_verifier import analyze_diagram

        with pytest.raises(FileNotFoundError):
            await analyze_diagram(str(tmp_path / "nonexistent.png"))


class TestVLMVerification:
    """Integration tests for VLM diagram verification."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_verify_diagram_returns_result(
        self, require_vlm, example_diagram_path, simple_spec
    ):
        """Test that verify_diagram returns valid VerificationResult."""
        from code_de_diagram.vlm_verifier import verify_diagram

        result = await verify_diagram(
            str(example_diagram_path),
            simple_spec,
        )

        assert isinstance(result, VerificationResult)
        assert isinstance(result.node_matches, list)
        assert isinstance(result.node_missing, list)
        assert isinstance(result.accuracy_score, float)
        assert 0.0 <= result.accuracy_score <= 1.0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_verify_diagram_with_precomputed_analysis(
        self, require_vlm, example_diagram_path, simple_spec
    ):
        """Test verify_diagram with pre-computed analysis."""
        from code_de_diagram.vlm_verifier import analyze_diagram, verify_diagram

        # First analyze
        analysis = await analyze_diagram(str(example_diagram_path))

        # Then verify with pre-computed analysis
        result = await verify_diagram(
            str(example_diagram_path),
            simple_spec,
            diagram_analysis=analysis,
        )

        assert isinstance(result, VerificationResult)
        assert 0.0 <= result.accuracy_score <= 1.0


class TestFullVerification:
    """Integration tests for full verification pipeline."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_full_verification_returns_complete_results(
        self, require_vlm, example_diagram_path, simple_spec
    ):
        """Test full_verification returns complete results dict."""
        from code_de_diagram.vlm_verifier import full_verification

        results = await full_verification(
            str(example_diagram_path),
            simple_spec,
        )

        assert isinstance(results, dict)
        assert "image_path" in results
        assert "expected" in results
        assert "analysis" in results
        assert "verification" in results

        # Check expected counts
        assert results["expected"]["nodes"] == len(simple_spec.nodes)
        assert results["expected"]["edges"] == len(simple_spec.edges)
        assert results["expected"]["clusters"] == len(simple_spec.clusters)

        # Check analysis results (if no error)
        if results["error"] is None:
            assert results["analysis"] is not None
            assert "components" in results["analysis"]
            assert "connections" in results["analysis"]

            assert results["verification"] is not None
            assert "accuracy_score" in results["verification"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_verification_handles_missing_file(
        self, require_vlm, simple_spec, tmp_path
    ):
        """Test full_verification handles missing image gracefully."""
        from code_de_diagram.vlm_verifier import full_verification

        results = await full_verification(
            str(tmp_path / "nonexistent.png"),
            simple_spec,
        )

        assert results["error"] is not None
        assert "not found" in results["error"].lower() or "No such file" in results["error"]
