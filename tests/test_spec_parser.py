"""Tests for the spec parser."""

import pytest
from pathlib import Path
from code_de_diagram.spec_parser import (
    parse_spec_file,
    get_expected_counts,
    spec_to_natural_language,
    _parse_node_type,
)
from code_de_diagram.models import NodeType, DiagramSpec


class TestParseNodeType:
    def test_aws_types(self):
        assert _parse_node_type("ec2") == NodeType.EC2
        assert _parse_node_type("lambda") == NodeType.LAMBDA
        assert _parse_node_type("alb") == NodeType.ALB
        assert _parse_node_type("rds") == NodeType.RDS
        assert _parse_node_type("s3") == NodeType.S3

    def test_case_insensitive(self):
        assert _parse_node_type("EC2") == NodeType.EC2
        assert _parse_node_type("Alb") == NodeType.ALB
        assert _parse_node_type("RDS") == NodeType.RDS

    def test_onprem_types(self):
        assert _parse_node_type("nginx") == NodeType.NGINX
        assert _parse_node_type("postgresql") == NodeType.POSTGRESQL

    def test_custom_types(self):
        assert _parse_node_type("ollama") == NodeType.OLLAMA
        assert _parse_node_type("lancedb") == NodeType.LANCEDB

    def test_unknown_defaults_to_generic(self):
        assert _parse_node_type("unknown") == NodeType.GENERIC_COMPUTE
        assert _parse_node_type("foo") == NodeType.GENERIC_COMPUTE


class TestParseSpecFile:
    def test_example_spec(self):
        """Test parsing the example SPEC.md file."""
        spec_path = Path(__file__).parent.parent / "example" / "SPEC.md"
        if not spec_path.exists():
            pytest.skip("Example SPEC.md not found")

        spec = parse_spec_file(spec_path)

        assert spec.name == "AWS Production VPC Architecture"
        assert spec.description is not None
        assert "aws" in spec.description.lower() or "availability" in spec.description.lower()

        # Check node counts
        assert len(spec.nodes) == 22

        # Check specific nodes exist
        node_ids = [n.id for n in spec.nodes]
        assert "alb" in node_ids
        assert "ec2_web_pub_1" in node_ids
        assert "aurora_1" in node_ids
        assert "nat_gw_1" in node_ids
        assert "waf" in node_ids

        # Check edges
        assert len(spec.edges) == 13

        # Check specific edges exist
        edge_pairs = [(e.source, e.target) for e in spec.edges]
        assert ("alb", "ec2_web_pub_1") in edge_pairs
        assert ("ec2_web_priv_1", "aurora_1") in edge_pairs

        # Check clusters
        assert len(spec.clusters) == 13

        # Check specific clusters
        cluster_ids = [c.id for c in spec.clusters]
        assert "production_vpc" in cluster_ids
        assert "az1" in cluster_ids
        assert "az2" in cluster_ids

    def test_parse_simple_spec(self, tmp_path):
        """Test parsing a simple spec file."""
        spec_content = """# Test Architecture

A simple test architecture.

## Description

This is a simple test architecture for unit testing.

## Components

### Compute
- **web**: Web Server | ec2 | Main web server
- **db**: Database | rds | Primary database

## Connections
- web -> db | TCP/5432

## Clusters
- **vpc**: My VPC | web, db
"""
        spec_file = tmp_path / "test.md"
        spec_file.write_text(spec_content)

        spec = parse_spec_file(spec_file)

        assert spec.name == "Test Architecture"
        assert "simple test architecture" in spec.description.lower()
        assert len(spec.nodes) == 2
        assert len(spec.edges) == 1
        assert len(spec.clusters) == 1

        # Check nodes
        web_node = next(n for n in spec.nodes if n.id == "web")
        assert web_node.label == "Web Server"
        assert web_node.node_type == NodeType.EC2

        # Check edges
        assert spec.edges[0].source == "web"
        assert spec.edges[0].target == "db"
        assert spec.edges[0].label == "TCP/5432"

        # Check clusters
        assert spec.clusters[0].label == "My VPC"
        assert "web" in spec.clusters[0].node_ids
        assert "db" in spec.clusters[0].node_ids


class TestGetExpectedCounts:
    def test_example_spec_expected_counts(self):
        """Test extracting expected counts from example SPEC.md."""
        spec_path = Path(__file__).parent.parent / "example" / "SPEC.md"
        if not spec_path.exists():
            pytest.skip("Example SPEC.md not found")

        counts = get_expected_counts(spec_path)

        assert counts["nodes"] == 22
        assert counts["edges"] == 13
        assert counts["clusters"] == 13

    def test_missing_expected_results(self, tmp_path):
        """Test when Expected Results section is missing."""
        spec_content = """# Test

## Components
- **web**: Web Server | ec2
"""
        spec_file = tmp_path / "test.md"
        spec_file.write_text(spec_content)

        counts = get_expected_counts(spec_file)

        assert counts["nodes"] is None
        assert counts["edges"] is None
        assert counts["clusters"] is None


class TestSpecToNaturalLanguage:
    def test_basic_conversion(self):
        """Test converting spec to natural language."""
        spec = DiagramSpec(
            name="My App",
            description="A web application",
            nodes=[
                {"id": "web", "label": "Web Server", "node_type": "ec2"},
                {"id": "db", "label": "Database", "node_type": "rds"},
            ],
            edges=[
                {"source": "web", "target": "db", "label": "SQL"},
            ],
            clusters=[
                {"id": "vpc", "label": "My VPC", "node_ids": ["web", "db"]},
            ],
        )

        result = spec_to_natural_language(spec)

        assert "My App" in result
        assert "A web application" in result
        assert "Web Server" in result
        assert "Database" in result
        assert "My VPC" in result
        assert "SQL" in result

    def test_empty_spec(self):
        """Test converting empty spec."""
        spec = DiagramSpec(name="Empty")
        result = spec_to_natural_language(spec)
        assert "Empty" in result
