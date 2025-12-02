"""Parser for SPEC.md files.

SPEC.md format:
    # Title
    Description text...

    ## Components
    ### Section Name
    - **id**: Label | node_type | description

    ## Connections
    - source -> target | label | description

    ## Clusters
    - **id**: Label | node_id1, node_id2
    - parent: parent_cluster_id
"""

import re
from pathlib import Path
from typing import Optional

from .models import (
    DiagramSpec,
    DiagramNode,
    DiagramEdge,
    DiagramCluster,
    NodeType,
)


def _parse_node_type(type_str: str) -> NodeType:
    """Convert string to NodeType enum."""
    type_map = {
        "ec2": NodeType.EC2,
        "lambda": NodeType.LAMBDA,
        "ecs": NodeType.ECS,
        "eks": NodeType.EKS,
        "vpc": NodeType.VPC,
        "alb": NodeType.ALB,
        "nlb": NodeType.NLB,
        "waf": NodeType.WAF,
        "route53": NodeType.ROUTE53,
        "cloudfront": NodeType.CLOUDFRONT,
        "api_gateway": NodeType.API_GATEWAY,
        "s3": NodeType.S3,
        "efs": NodeType.EFS,
        "ebs": NodeType.EBS,
        "rds": NodeType.RDS,
        "aurora": NodeType.AURORA,
        "dynamodb": NodeType.DYNAMODB,
        "elasticache": NodeType.ELASTICACHE,
        "sqs": NodeType.SQS,
        "sns": NodeType.SNS,
        "kinesis": NodeType.KINESIS,
        "nginx": NodeType.NGINX,
        "postgresql": NodeType.POSTGRESQL,
        "generic_compute": NodeType.GENERIC_COMPUTE,
        "generic_database": NodeType.GENERIC_DATABASE,
        "generic_storage": NodeType.GENERIC_STORAGE,
        "ollama": NodeType.OLLAMA,
        "lancedb": NodeType.LANCEDB,
        "custom": NodeType.CUSTOM,
    }
    return type_map.get(type_str.lower().strip(), NodeType.GENERIC_COMPUTE)


def parse_spec_file(filepath: str | Path) -> DiagramSpec:
    """Parse a SPEC.md file into a DiagramSpec."""
    filepath = Path(filepath)
    content = filepath.read_text()

    # Extract title from first H1
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    name = title_match.group(1).strip() if title_match else "Diagram"

    # Extract description - check for ## Description section first
    description = None
    desc_section_match = re.search(
        r'##\s+Description\s*\n(.*?)(?=\n##\s+[A-Z]|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if desc_section_match:
        description = desc_section_match.group(1).strip()
    else:
        # Fallback: text between H1 title and first ##
        desc_match = re.search(r'^#\s+.+\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()

    nodes = []
    edges = []
    clusters = []

    # Parse Components section
    components_match = re.search(
        r'##\s+Components\s*\n(.*?)(?=\n##\s+[A-Z]|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if components_match:
        components_text = components_match.group(1)
        # Match: - **id**: Label | node_type | description
        node_pattern = re.compile(
            r'-\s+\*\*(\w+)\*\*:\s*([^|]+)\|\s*(\w+)(?:\s*\|\s*(.+))?',
            re.MULTILINE
        )
        for match in node_pattern.finditer(components_text):
            node_id = match.group(1).strip()
            label = match.group(2).strip()
            node_type = _parse_node_type(match.group(3))
            desc = match.group(4).strip() if match.group(4) else None
            nodes.append(DiagramNode(
                id=node_id,
                label=label,
                node_type=node_type,
                description=desc,
            ))

    # Parse Connections section
    connections_match = re.search(
        r'##\s+Connections\s*\n(.*?)(?=\n##\s+[A-Z]|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if connections_match:
        connections_text = connections_match.group(1)
        # Match: - source -> target | label | description
        edge_pattern = re.compile(
            r'-\s+(\w+)\s*->\s*(\w+)(?:\s*\|\s*([^|\n]+))?(?:\s*\|\s*([^\n]+))?',
            re.MULTILINE
        )
        for match in edge_pattern.finditer(connections_text):
            source = match.group(1).strip()
            target = match.group(2).strip()
            label = match.group(3).strip() if match.group(3) else None
            edges.append(DiagramEdge(
                source=source,
                target=target,
                label=label,
            ))

    # Parse Clusters section
    clusters_match = re.search(
        r'##\s+Clusters\s*\n(.*?)(?=\n##\s+[A-Z]|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if clusters_match:
        clusters_text = clusters_match.group(1)
        # Split by cluster headers (###) or bullet definitions
        # Match: - **id**: Label | node_id1, node_id2
        cluster_pattern = re.compile(
            r'-\s+\*\*(\w+)\*\*:\s*([^|\n]+)\|\s*([^\n]+)',
            re.MULTILINE
        )
        parent_pattern = re.compile(r'-\s+parent:\s*(\w+)', re.MULTILINE)

        # Find all clusters and their positions
        cluster_matches = list(cluster_pattern.finditer(clusters_text))
        parent_matches = list(parent_pattern.finditer(clusters_text))

        for i, match in enumerate(cluster_matches):
            cluster_id = match.group(1).strip()
            label = match.group(2).strip()
            node_ids_str = match.group(3).strip()
            node_ids = [n.strip() for n in node_ids_str.split(',') if n.strip()]

            # Check for parent in lines following this cluster
            parent_id = None
            match_end = match.end()
            next_cluster_start = cluster_matches[i + 1].start() if i + 1 < len(cluster_matches) else len(clusters_text)

            for pm in parent_matches:
                if match_end < pm.start() < next_cluster_start:
                    parent_id = pm.group(1).strip()
                    break

            clusters.append(DiagramCluster(
                id=cluster_id,
                label=label,
                node_ids=node_ids,
                parent_cluster_id=parent_id,
            ))

    return DiagramSpec(
        name=name,
        description=description,
        direction="TB",
        nodes=nodes,
        edges=edges,
        clusters=clusters,
    )


def get_expected_counts(filepath: str | Path) -> dict:
    """Extract expected counts from SPEC.md for evaluation."""
    filepath = Path(filepath)
    content = filepath.read_text()

    counts = {
        "nodes": None,
        "edges": None,
        "clusters": None,
    }

    # Look for Expected Results section (match until next H2 but not H3, or end of file)
    expected_match = re.search(
        r'##\s+Expected Results\s*\n(.*?)(?=\n## [A-Z]|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    if expected_match:
        expected_text = expected_match.group(1)

        # Match patterns like "### Node Count\n- Total: 16 nodes"
        node_match = re.search(r'Node Count.*?-\s*Total:\s*(\d+)', expected_text, re.DOTALL | re.IGNORECASE)
        if node_match:
            counts["nodes"] = int(node_match.group(1))

        edge_match = re.search(r'Edge Count.*?-\s*Total:\s*(\d+)', expected_text, re.DOTALL | re.IGNORECASE)
        if edge_match:
            counts["edges"] = int(edge_match.group(1))

        cluster_match = re.search(r'Cluster Count.*?-\s*Total:\s*(\d+)', expected_text, re.DOTALL | re.IGNORECASE)
        if cluster_match:
            counts["clusters"] = int(cluster_match.group(1))

    return counts


def spec_to_natural_language(spec: DiagramSpec) -> str:
    """Convert a DiagramSpec to natural language description for LLM."""
    lines = [f"Create a diagram for: {spec.name}"]

    if spec.description:
        lines.append(f"\n{spec.description}")

    if spec.nodes:
        lines.append("\n## Components:")
        for node in spec.nodes:
            desc = f" - {node.description}" if node.description else ""
            lines.append(f"- {node.label} ({node.node_type.value}){desc}")

    if spec.clusters:
        lines.append("\n## Groupings:")
        for cluster in spec.clusters:
            node_labels = []
            for nid in cluster.node_ids:
                node = next((n for n in spec.nodes if n.id == nid), None)
                if node:
                    node_labels.append(node.label)
            if node_labels:
                lines.append(f"- {cluster.label}: {', '.join(node_labels)}")

    if spec.edges:
        lines.append("\n## Connections:")
        for edge in spec.edges:
            src = next((n for n in spec.nodes if n.id == edge.source), None)
            tgt = next((n for n in spec.nodes if n.id == edge.target), None)
            src_label = src.label if src else edge.source
            tgt_label = tgt.label if tgt else edge.target
            label = f" ({edge.label})" if edge.label else ""
            lines.append(f"- {src_label} -> {tgt_label}{label}")

    return "\n".join(lines)
