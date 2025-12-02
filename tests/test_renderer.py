"""Tests for the renderer."""

import pytest
from code_de_diagram.models import (
    NodeType,
    DiagramNode,
    DiagramEdge,
    DiagramCluster,
    DiagramSpec,
)
from code_de_diagram.renderer import (
    DiagramRenderer,
    render_spec_to_code,
    NODE_TYPE_IMPORTS,
)


class TestNodeTypeImports:
    def test_aws_compute_mappings(self):
        assert NODE_TYPE_IMPORTS[NodeType.EC2] == ("diagrams.aws.compute", "EC2")
        assert NODE_TYPE_IMPORTS[NodeType.LAMBDA] == ("diagrams.aws.compute", "Lambda")

    def test_aws_network_mappings(self):
        assert NODE_TYPE_IMPORTS[NodeType.ALB] == ("diagrams.aws.network", "ALB")
        assert NODE_TYPE_IMPORTS[NodeType.WAF] == ("diagrams.aws.security", "WAF")

    def test_aws_storage_mappings(self):
        assert NODE_TYPE_IMPORTS[NodeType.S3] == ("diagrams.aws.storage", "S3")

    def test_aws_database_mappings(self):
        assert NODE_TYPE_IMPORTS[NodeType.RDS] == ("diagrams.aws.database", "RDS")

    def test_onprem_mappings(self):
        assert NODE_TYPE_IMPORTS[NodeType.NGINX] == ("diagrams.onprem.network", "Nginx")
        assert NODE_TYPE_IMPORTS[NodeType.POSTGRESQL] == ("diagrams.onprem.database", "PostgreSQL")

    def test_custom_fallbacks(self):
        assert NODE_TYPE_IMPORTS[NodeType.OLLAMA] == ("diagrams.onprem.compute", "Server")
        assert NODE_TYPE_IMPORTS[NodeType.LANCEDB] == ("diagrams.onprem.compute", "Server")
        assert NODE_TYPE_IMPORTS[NodeType.CUSTOM] == ("diagrams.onprem.compute", "Server")


class TestDiagramRenderer:
    def test_sanitize_var_name(self):
        renderer = DiagramRenderer(DiagramSpec(name="Test"))
        assert renderer._sanitize_var_name("web-server-1") == "web_server_1"
        assert renderer._sanitize_var_name("123abc") == "n_123abc"
        assert renderer._sanitize_var_name("MyNode") == "mynode"
        assert renderer._sanitize_var_name("node@#$%") == "node____"

    def test_get_node_class(self):
        renderer = DiagramRenderer(DiagramSpec(name="Test"))
        node = DiagramNode(id="web", label="Web", node_type=NodeType.EC2)
        class_name = renderer._get_node_class(node)
        assert class_name == "EC2"
        assert ("diagrams.aws.compute", "EC2") in renderer._imports

    def test_generate_imports_single(self):
        renderer = DiagramRenderer(DiagramSpec(name="Test"))
        renderer._imports.add(("diagrams.aws.compute", "EC2"))
        imports = renderer._generate_imports()
        assert "from diagrams import Diagram, Cluster, Edge" in imports
        assert "from diagrams.aws.compute import EC2" in imports

    def test_generate_imports_grouped(self):
        renderer = DiagramRenderer(DiagramSpec(name="Test"))
        renderer._imports.add(("diagrams.aws.compute", "EC2"))
        renderer._imports.add(("diagrams.aws.compute", "Lambda"))
        imports = renderer._generate_imports()
        assert "from diagrams.aws.compute import EC2, Lambda" in imports

    def test_generate_node(self):
        renderer = DiagramRenderer(DiagramSpec(name="Test"))
        node = DiagramNode(id="web1", label="Web Server", node_type=NodeType.EC2)
        code = renderer._generate_node(node, indent=1)
        assert 'web1 = EC2("Web Server")' in code
        assert renderer._node_vars["web1"] == "web1"

    def test_generate_edge_with_label(self):
        spec = DiagramSpec(
            name="Test",
            nodes=[
                DiagramNode(id="a", label="A", node_type=NodeType.EC2),
                DiagramNode(id="b", label="B", node_type=NodeType.RDS),
            ],
            edges=[DiagramEdge(source="a", target="b", label="TCP/5432")],
        )
        renderer = DiagramRenderer(spec)
        # Generate nodes first to populate _node_vars
        renderer._generate_node(spec.nodes[0])
        renderer._generate_node(spec.nodes[1])
        edges = renderer._generate_edges()
        assert any('Edge(label="TCP/5432")' in line for line in edges)

    def test_generate_cluster(self):
        spec = DiagramSpec(
            name="Test",
            nodes=[
                DiagramNode(id="web1", label="Web 1", node_type=NodeType.NGINX),
                DiagramNode(id="web2", label="Web 2", node_type=NodeType.NGINX),
            ],
            clusters=[
                DiagramCluster(id="web", label="Web Tier", node_ids=["web1", "web2"]),
            ],
        )
        renderer = DiagramRenderer(spec)
        cluster_code = renderer._generate_cluster(spec.clusters[0])
        assert any('with Cluster("Web Tier"):' in line for line in cluster_code)


class TestRenderSpecToCode:
    def test_simple_spec(self):
        spec = DiagramSpec(
            name="Simple Test",
            direction="TB",
            nodes=[
                DiagramNode(id="alb", label="Load Balancer", node_type=NodeType.ALB),
                DiagramNode(id="web", label="Web Server", node_type=NodeType.EC2),
            ],
            edges=[
                DiagramEdge(source="alb", target="web"),
            ],
        )
        code = render_spec_to_code(spec, "test_output")
        assert "from diagrams import Diagram, Cluster, Edge" in code
        assert "from diagrams.aws.compute import EC2" in code
        assert "from diagrams.aws.network import ALB" in code
        assert 'alb = ALB("Load Balancer")' in code
        assert 'web = EC2("Web Server")' in code
        assert 'filename="test_output"' in code
        assert 'direction="TB"' in code

    def test_spec_with_clusters(self):
        spec = DiagramSpec(
            name="Clustered",
            nodes=[
                DiagramNode(id="nginx1", label="NGINX 1", node_type=NodeType.NGINX),
                DiagramNode(id="nginx2", label="NGINX 2", node_type=NodeType.NGINX),
            ],
            clusters=[
                DiagramCluster(id="web", label="Web Tier", node_ids=["nginx1", "nginx2"]),
            ],
        )
        code = render_spec_to_code(spec)
        assert 'with Cluster("Web Tier"):' in code
        assert 'nginx1 = Nginx("NGINX 1")' in code

    def test_spec_with_edge_labels(self):
        spec = DiagramSpec(
            name="Labeled Edges",
            nodes=[
                DiagramNode(id="web", label="Web", node_type=NodeType.EC2),
                DiagramNode(id="db", label="DB", node_type=NodeType.RDS),
            ],
            edges=[
                DiagramEdge(source="web", target="db", label="TCP/5432"),
            ],
        )
        code = render_spec_to_code(spec)
        assert 'Edge(label="TCP/5432")' in code

    def test_graph_attributes(self):
        spec = DiagramSpec(name="Test")
        code = render_spec_to_code(spec)
        assert '"splines": "ortho"' in code
        assert '"nodesep": "0.8"' in code
        assert '"ranksep": "1.0"' in code
        assert "graph_attr=graph_attr" in code

    def test_show_false(self):
        spec = DiagramSpec(name="Test")
        code = render_spec_to_code(spec)
        assert "show=False" in code
