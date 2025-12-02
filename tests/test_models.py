"""Tests for data models."""

import pytest
from code_de_diagram.models import (
    NodeType,
    EdgeStyle,
    DiagramNode,
    DiagramEdge,
    DiagramCluster,
    DiagramSpec,
    ClarifyingQuestion,
    ConversationMessage,
)


class TestNodeType:
    def test_aws_types(self):
        assert NodeType.EC2 == "ec2"
        assert NodeType.ALB == "alb"
        assert NodeType.S3 == "s3"
        assert NodeType.RDS == "rds"

    def test_onprem_types(self):
        assert NodeType.NGINX == "nginx"
        assert NodeType.POSTGRESQL == "postgresql"

    def test_custom_types(self):
        assert NodeType.OLLAMA == "ollama"
        assert NodeType.LANCEDB == "lancedb"
        assert NodeType.CUSTOM == "custom"


class TestEdgeStyle:
    def test_styles(self):
        assert EdgeStyle.SOLID == "solid"
        assert EdgeStyle.DASHED == "dashed"
        assert EdgeStyle.DOTTED == "dotted"


class TestDiagramNode:
    def test_basic_node(self):
        node = DiagramNode(id="web1", label="Web Server", node_type=NodeType.EC2)
        assert node.id == "web1"
        assert node.label == "Web Server"
        assert node.node_type == NodeType.EC2
        assert node.description is None
        assert node.icon_url is None

    def test_node_with_optional_fields(self):
        node = DiagramNode(
            id="custom1",
            label="Custom Service",
            node_type=NodeType.CUSTOM,
            description="A custom service",
            icon_url="https://example.com/icon.png",
        )
        assert node.description == "A custom service"
        assert node.icon_url == "https://example.com/icon.png"

    def test_node_serialization(self):
        node = DiagramNode(id="db", label="Database", node_type=NodeType.RDS)
        data = node.model_dump()
        assert data["id"] == "db"
        assert data["node_type"] == "rds"


class TestDiagramEdge:
    def test_basic_edge(self):
        edge = DiagramEdge(source="a", target="b")
        assert edge.source == "a"
        assert edge.target == "b"
        assert edge.label is None
        assert edge.style == EdgeStyle.SOLID
        assert edge.bidirectional is False

    def test_edge_with_label(self):
        edge = DiagramEdge(source="web", target="db", label="TCP/5432")
        assert edge.label == "TCP/5432"

    def test_bidirectional_edge(self):
        edge = DiagramEdge(source="a", target="b", bidirectional=True)
        assert edge.bidirectional is True


class TestDiagramCluster:
    def test_basic_cluster(self):
        cluster = DiagramCluster(id="web_tier", label="Web Tier")
        assert cluster.id == "web_tier"
        assert cluster.label == "Web Tier"
        assert cluster.node_ids == []
        assert cluster.parent_cluster_id is None

    def test_cluster_with_nodes(self):
        cluster = DiagramCluster(
            id="web_tier",
            label="Web Tier",
            node_ids=["web1", "web2", "web3"],
        )
        assert len(cluster.node_ids) == 3
        assert "web1" in cluster.node_ids

    def test_nested_cluster(self):
        cluster = DiagramCluster(
            id="private_subnet",
            label="Private Subnet",
            parent_cluster_id="vpc",
        )
        assert cluster.parent_cluster_id == "vpc"


class TestDiagramSpec:
    def test_empty_spec(self):
        spec = DiagramSpec(name="Test Diagram")
        assert spec.name == "Test Diagram"
        assert spec.description is None
        assert spec.direction == "TB"
        assert spec.nodes == []
        assert spec.edges == []
        assert spec.clusters == []

    def test_full_spec(self):
        spec = DiagramSpec(
            name="RAG Pipeline",
            description="A RAG system",
            direction="LR",
            nodes=[
                DiagramNode(id="waf", label="WAF", node_type=NodeType.WAF),
                DiagramNode(id="nginx", label="NGINX", node_type=NodeType.NGINX),
            ],
            edges=[
                DiagramEdge(source="waf", target="nginx", label="HTTPS/443"),
            ],
            clusters=[
                DiagramCluster(id="web", label="Web Tier", node_ids=["nginx"]),
            ],
        )
        assert len(spec.nodes) == 2
        assert len(spec.edges) == 1
        assert len(spec.clusters) == 1
        assert spec.direction == "LR"

    def test_spec_json_roundtrip(self):
        spec = DiagramSpec(
            name="Test",
            nodes=[DiagramNode(id="a", label="A", node_type=NodeType.EC2)],
        )
        json_str = spec.model_dump_json()
        loaded = DiagramSpec.model_validate_json(json_str)
        assert loaded.name == spec.name
        assert len(loaded.nodes) == 1
        assert loaded.nodes[0].id == "a"


class TestClarifyingQuestion:
    def test_basic_question(self):
        q = ClarifyingQuestion(
            question="How many servers?",
            context="Need to know for scaling",
        )
        assert q.question == "How many servers?"
        assert q.context == "Need to know for scaling"
        assert q.options is None
        assert q.default is None

    def test_question_with_options(self):
        q = ClarifyingQuestion(
            question="What database?",
            context="For data storage",
            options=["PostgreSQL", "MySQL", "DynamoDB"],
            default="PostgreSQL",
        )
        assert len(q.options) == 3
        assert q.default == "PostgreSQL"


class TestConversationMessage:
    def test_user_message(self):
        msg = ConversationMessage(role="user", content="Create a diagram")
        assert msg.role == "user"
        assert msg.content == "Create a diagram"

    def test_assistant_message(self):
        msg = ConversationMessage(role="assistant", content="Sure, I'll help")
        assert msg.role == "assistant"
