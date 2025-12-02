"""Deterministic renderer: DiagramSpec -> Python diagrams code."""

import os
import sys
import subprocess
import tempfile

from .models import DiagramSpec, DiagramNode, DiagramCluster, NodeType


NODE_TYPE_IMPORTS = {
    NodeType.EC2: ("diagrams.aws.compute", "EC2"),
    NodeType.LAMBDA: ("diagrams.aws.compute", "Lambda"),
    NodeType.ECS: ("diagrams.aws.compute", "ECS"),
    NodeType.EKS: ("diagrams.aws.compute", "EKS"),
    NodeType.VPC: ("diagrams.aws.network", "VPC"),
    NodeType.ALB: ("diagrams.aws.network", "ALB"),
    NodeType.NLB: ("diagrams.aws.network", "NLB"),
    NodeType.WAF: ("diagrams.aws.security", "WAF"),
    NodeType.ROUTE53: ("diagrams.aws.network", "Route53"),
    NodeType.CLOUDFRONT: ("diagrams.aws.network", "CloudFront"),
    NodeType.API_GATEWAY: ("diagrams.aws.network", "APIGateway"),
    NodeType.S3: ("diagrams.aws.storage", "S3"),
    NodeType.EFS: ("diagrams.aws.storage", "EFS"),
    NodeType.EBS: ("diagrams.aws.storage", "EBS"),
    NodeType.RDS: ("diagrams.aws.database", "RDS"),
    NodeType.AURORA: ("diagrams.aws.database", "Aurora"),
    NodeType.DYNAMODB: ("diagrams.aws.database", "Dynamodb"),
    NodeType.ELASTICACHE: ("diagrams.aws.database", "ElastiCache"),
    NodeType.SQS: ("diagrams.aws.integration", "SQS"),
    NodeType.SNS: ("diagrams.aws.integration", "SNS"),
    NodeType.KINESIS: ("diagrams.aws.analytics", "Kinesis"),
    NodeType.NGINX: ("diagrams.onprem.network", "Nginx"),
    NodeType.POSTGRESQL: ("diagrams.onprem.database", "PostgreSQL"),
    NodeType.GENERIC_COMPUTE: ("diagrams.onprem.compute", "Server"),
    NodeType.GENERIC_DATABASE: ("diagrams.onprem.database", "PostgreSQL"),
    NodeType.GENERIC_STORAGE: ("diagrams.aws.storage", "S3"),
    NodeType.OLLAMA: ("diagrams.onprem.compute", "Server"),
    NodeType.LANCEDB: ("diagrams.onprem.compute", "Server"),
    NodeType.CUSTOM: ("diagrams.onprem.compute", "Server"),
}


def _validate_node_type_mappings():
    """Validate all NodeType enum values have import mappings. Fails at module load."""
    missing = [nt for nt in NodeType if nt not in NODE_TYPE_IMPORTS]
    if missing:
        missing_names = [nt.value for nt in missing]
        raise ValueError(
            f"NODE_TYPE_IMPORTS missing mappings for: {missing_names}. "
            "Add entries to NODE_TYPE_IMPORTS in renderer.py"
        )


# Validate at module load time
_validate_node_type_mappings()


def validate_spec_node_types(spec: DiagramSpec) -> list[str]:
    """Validate all nodes in spec have valid, mapped types.

    Returns list of error messages (empty if valid).
    """
    errors = []
    for node in spec.nodes:
        if node.node_type not in NODE_TYPE_IMPORTS:
            errors.append(
                f"Node '{node.id}' has unmapped type '{node.node_type.value}'. "
                f"Add mapping to NODE_TYPE_IMPORTS in renderer.py"
            )
    return errors


def get_node_type_info(node_type: NodeType) -> tuple[str, str]:
    """Get the (module, class_name) for a NodeType.

    Raises ValueError if node_type is not mapped.
    """
    if node_type not in NODE_TYPE_IMPORTS:
        raise ValueError(
            f"NodeType '{node_type.value}' has no import mapping. "
            f"Add entry to NODE_TYPE_IMPORTS in renderer.py"
        )
    return NODE_TYPE_IMPORTS[node_type]


class DiagramRenderer:
    """Renders DiagramSpec to executable Python code."""

    def __init__(self, spec: DiagramSpec, output_filename: str = "diagram"):
        self.spec = spec
        self.output_filename = output_filename
        self._imports: set[tuple[str, str]] = set()
        self._node_vars: dict[str, str] = {}

    def _sanitize_var_name(self, name: str) -> str:
        sanitized = "".join(c if c.isalnum() else "_" for c in name.lower())
        if sanitized and sanitized[0].isdigit():
            sanitized = "n_" + sanitized
        return sanitized or "node"

    def _get_node_class(self, node: DiagramNode) -> str:
        if node.node_type in NODE_TYPE_IMPORTS:
            module, class_name = NODE_TYPE_IMPORTS[node.node_type]
            self._imports.add((module, class_name))
            return class_name
        self._imports.add(("diagrams.onprem.compute", "Server"))
        return "Server"

    def _generate_imports(self) -> str:
        lines = ["from diagrams import Diagram, Cluster, Edge"]
        by_module: dict[str, list[str]] = {}
        for module, class_name in sorted(self._imports):
            by_module.setdefault(module, []).append(class_name)
        for module in sorted(by_module):
            classes = ", ".join(sorted(by_module[module]))
            lines.append(f"from {module} import {classes}")
        return "\n".join(lines)

    def _generate_node(self, node: DiagramNode, indent: int = 1) -> str:
        prefix = "    " * indent
        var_name = self._sanitize_var_name(node.id)
        self._node_vars[node.id] = var_name
        class_name = self._get_node_class(node)
        label = node.label.replace('"', '\\"').replace('\n', '\\n')
        return f'{prefix}{var_name} = {class_name}("{label}")'

    def _generate_cluster(self, cluster: DiagramCluster, indent: int = 1) -> list[str]:
        lines = []
        prefix = "    " * indent
        label = cluster.label.replace('"', '\\"')
        lines.append(f'{prefix}with Cluster("{label}"):')

        nodes_in_cluster = [n for n in self.spec.nodes if n.id in cluster.node_ids]
        for node in nodes_in_cluster:
            lines.append(self._generate_node(node, indent + 1))

        child_clusters = [c for c in self.spec.clusters if c.parent_cluster_id == cluster.id]
        for child in child_clusters:
            lines.extend(self._generate_cluster(child, indent + 1))

        if not nodes_in_cluster and not child_clusters:
            lines.append(f'{prefix}    pass')
        return lines

    def _generate_edges(self, indent: int = 1) -> list[str]:
        lines = []
        prefix = "    " * indent
        if self.spec.edges:
            lines.append(f"{prefix}")
            lines.append(f"{prefix}# Connections")
        for edge in self.spec.edges:
            src = self._node_vars.get(edge.source, edge.source)
            tgt = self._node_vars.get(edge.target, edge.target)
            if edge.label:
                label = edge.label.replace('"', '\\"').replace('\n', '\\n')
                op = "<<" if edge.bidirectional else ">>"
                lines.append(f'{prefix}{src} {op} Edge(label="{label}") >> {tgt}')
            else:
                op = "<< Edge() >>" if edge.bidirectional else ">>"
                lines.append(f'{prefix}{src} {op} {tgt}')
        return lines

    def render(self) -> str:
        body_lines = []
        clustered_ids = {nid for c in self.spec.clusters for nid in c.node_ids}

        for node in self.spec.nodes:
            if node.id not in clustered_ids:
                body_lines.append(self._generate_node(node))

        for cluster in self.spec.clusters:
            if cluster.parent_cluster_id is None:
                body_lines.extend(self._generate_cluster(cluster))

        body_lines.extend(self._generate_edges())
        imports = self._generate_imports()
        name = self.spec.name.replace('"', '\\"')

        return f'''{imports}

graph_attr = {{"splines": "ortho", "nodesep": "0.8", "ranksep": "1.0"}}

with Diagram("{name}", show=False, filename="{self.output_filename}", direction="{self.spec.direction}", graph_attr=graph_attr):
{chr(10).join(body_lines)}
'''


def render_spec_to_code(spec: DiagramSpec, output_filename: str = "diagram") -> str:
    """Render a DiagramSpec to Python code.

    Raises ValueError if any node types are unmapped.
    """
    errors = validate_spec_node_types(spec)
    if errors:
        raise ValueError(f"Invalid node types in spec:\n" + "\n".join(errors))
    return DiagramRenderer(spec, output_filename).render()


def render_and_execute(spec: DiagramSpec, output_filename: str = "diagram") -> tuple[bool, str, str]:
    """Render and execute, returning (success, message, code)."""
    code = render_spec_to_code(spec, output_filename)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            png_path = f"{output_filename}.png"
            if os.path.exists(png_path):
                return True, f"Diagram generated: {png_path}", code
            return True, f"Code executed: {result.stdout}", code
        return False, f"Failed: {result.stderr}", code
    except subprocess.TimeoutExpired:
        return False, "Timeout", code
    except Exception as e:
        return False, str(e), code
    finally:
        os.unlink(temp_path)
