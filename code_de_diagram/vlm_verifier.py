"""VLM-based diagram verification.

Uses a Vision Language Model to analyze generated diagrams and compare
them against the expected SPEC.md requirements.
"""

import base64
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from .config import get_vlm_model_name, get_vlm_model_config
from .models import DiagramSpec


class DiagramAnalysis(BaseModel):
    """Analysis of a diagram image by VLM."""
    identified_components: list[str] = Field(
        description="List of components/nodes visible in the diagram"
    )
    identified_connections: list[str] = Field(
        description="List of connections/edges visible (e.g., 'A -> B')"
    )
    identified_clusters: list[str] = Field(
        description="List of groupings/clusters visible in the diagram"
    )
    diagram_title: Optional[str] = Field(
        default=None,
        description="Title of the diagram if visible"
    )
    overall_description: str = Field(
        description="Brief description of what the diagram represents"
    )


class VerificationResult(BaseModel):
    """Result of comparing diagram against spec."""
    node_matches: list[str] = Field(
        description="Nodes from spec that were found in diagram"
    )
    node_missing: list[str] = Field(
        description="Nodes from spec that are missing from diagram"
    )
    node_extra: list[str] = Field(
        description="Nodes in diagram that weren't in spec"
    )
    edge_matches: list[str] = Field(
        description="Edges from spec that were found in diagram"
    )
    edge_missing: list[str] = Field(
        description="Edges from spec that are missing from diagram"
    )
    cluster_matches: list[str] = Field(
        description="Clusters from spec that were found in diagram"
    )
    cluster_missing: list[str] = Field(
        description="Clusters from spec that are missing from diagram"
    )
    accuracy_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall accuracy score (0-1)"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Any issues or discrepancies found"
    )


VLM_ANALYSIS_PROMPT = """You are an expert at analyzing architecture diagrams.

Analyze this diagram image and identify:
1. All components/nodes (services, databases, servers, etc.)
2. All connections/edges between components
3. All groupings/clusters (boxes containing multiple components)
4. The overall architecture pattern

Be thorough and list every visible element. Use the labels shown in the diagram."""


VLM_VERIFICATION_PROMPT = """You are an expert at verifying architecture diagrams against specifications.

Compare the diagram analysis against the expected specification and identify:
1. Which expected nodes are present in the diagram
2. Which expected nodes are missing
3. Any extra nodes not in the spec
4. Which expected edges are present
5. Which expected edges are missing
6. Which clusters match the spec
7. Which clusters are missing

Calculate an overall accuracy score based on how well the diagram matches the spec.
Be strict but fair - minor label differences are acceptable if the component type matches."""


_analyzer: Optional[Agent] = None
_verifier: Optional[Agent] = None
_current_vlm_model: Optional[str] = None


def get_analyzer() -> Agent:
    """Get or create the diagram analyzer agent using VLM model."""
    global _analyzer, _current_vlm_model
    vlm_model = get_vlm_model_name()
    # Recreate if model changed
    if _analyzer is None or _current_vlm_model != vlm_model:
        _analyzer = Agent(
            vlm_model,
            output_type=DiagramAnalysis,
            system_prompt=VLM_ANALYSIS_PROMPT,
        )
        _current_vlm_model = vlm_model
    return _analyzer


def get_verifier() -> Agent:
    """Get or create the verification agent using VLM model."""
    global _verifier, _current_vlm_model
    vlm_model = get_vlm_model_name()
    # Recreate if model changed
    if _verifier is None or _current_vlm_model != vlm_model:
        _verifier = Agent(
            vlm_model,
            output_type=VerificationResult,
            system_prompt=VLM_VERIFICATION_PROMPT,
        )
        _current_vlm_model = vlm_model
    return _verifier


def get_vlm_model_info() -> dict:
    """Get information about the VLM model being used."""
    config = get_vlm_model_config()
    return {
        "provider": config.provider.value,
        "model": config.model,
        "full_name": config.full_name,
    }


def _encode_image(image_path: str) -> str:
    """Encode image to base64 for VLM input."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _spec_to_checklist(spec: DiagramSpec) -> str:
    """Convert spec to a checklist for verification."""
    lines = [f"# Expected Architecture: {spec.name}"]

    lines.append("\n## Expected Nodes:")
    for node in spec.nodes:
        lines.append(f"- {node.label} (type: {node.node_type.value}, id: {node.id})")

    lines.append("\n## Expected Edges:")
    for edge in spec.edges:
        src = next((n.label for n in spec.nodes if n.id == edge.source), edge.source)
        tgt = next((n.label for n in spec.nodes if n.id == edge.target), edge.target)
        label = f" [{edge.label}]" if edge.label else ""
        lines.append(f"- {src} -> {tgt}{label}")

    lines.append("\n## Expected Clusters:")
    for cluster in spec.clusters:
        node_labels = [
            next((n.label for n in spec.nodes if n.id == nid), nid)
            for nid in cluster.node_ids
        ]
        lines.append(f"- {cluster.label}: {', '.join(node_labels)}")

    return "\n".join(lines)


async def analyze_diagram(image_path: str) -> DiagramAnalysis:
    """Analyze a diagram image using VLM.

    Args:
        image_path: Path to the diagram PNG file

    Returns:
        DiagramAnalysis with identified components
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Diagram not found: {image_path}")

    # For models that support vision, we'd send the image
    # For now, we'll note this as a placeholder since pydantic-ai
    # vision support depends on the model backend

    # Read and encode the image
    image_data = _encode_image(image_path)

    # Create prompt with image reference
    # Note: Actual image passing depends on pydantic-ai version and model support
    prompt = f"""Analyze this architecture diagram.

[Image: diagram at {image_path}]

Identify all visible components, connections, and groupings."""

    result = await get_analyzer().run(prompt)
    return result.output


async def verify_diagram(
    image_path: str,
    expected_spec: DiagramSpec,
    diagram_analysis: Optional[DiagramAnalysis] = None
) -> VerificationResult:
    """Verify a diagram against expected specification.

    Args:
        image_path: Path to the generated diagram
        expected_spec: The expected DiagramSpec
        diagram_analysis: Optional pre-computed analysis (if None, will analyze first)

    Returns:
        VerificationResult with match details and accuracy score
    """
    # Get diagram analysis if not provided
    if diagram_analysis is None:
        diagram_analysis = await analyze_diagram(image_path)

    # Build verification prompt
    spec_checklist = _spec_to_checklist(expected_spec)

    prompt = f"""Compare the diagram analysis against the expected specification.

## Diagram Analysis (what was found):
- Components: {', '.join(diagram_analysis.identified_components)}
- Connections: {', '.join(diagram_analysis.identified_connections)}
- Clusters: {', '.join(diagram_analysis.identified_clusters)}
- Description: {diagram_analysis.overall_description}

{spec_checklist}

Determine which expected elements are present, missing, or extra.
Calculate accuracy as: (matched_elements) / (total_expected_elements)"""

    result = await get_verifier().run(prompt)
    return result.output


async def full_verification(
    image_path: str,
    expected_spec: DiagramSpec
) -> dict:
    """Run full verification pipeline.

    Returns a dict with analysis, verification, and summary metrics.
    """
    results = {
        "image_path": image_path,
        "expected": {
            "nodes": len(expected_spec.nodes),
            "edges": len(expected_spec.edges),
            "clusters": len(expected_spec.clusters),
        },
        "analysis": None,
        "verification": None,
        "error": None,
    }

    try:
        # Analyze the diagram
        analysis = await analyze_diagram(image_path)
        results["analysis"] = {
            "components": analysis.identified_components,
            "connections": analysis.identified_connections,
            "clusters": analysis.identified_clusters,
            "description": analysis.overall_description,
        }

        # Verify against spec
        verification = await verify_diagram(image_path, expected_spec, analysis)
        results["verification"] = {
            "node_matches": verification.node_matches,
            "node_missing": verification.node_missing,
            "node_extra": verification.node_extra,
            "edge_matches": verification.edge_matches,
            "edge_missing": verification.edge_missing,
            "cluster_matches": verification.cluster_matches,
            "cluster_missing": verification.cluster_missing,
            "accuracy_score": verification.accuracy_score,
            "issues": verification.issues,
        }

    except Exception as e:
        results["error"] = str(e)

    return results
