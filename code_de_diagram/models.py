"""Pydantic models for diagram specifications."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Supported node types."""
    # AWS Compute
    EC2 = "ec2"
    LAMBDA = "lambda"
    ECS = "ecs"
    EKS = "eks"
    # AWS Network
    VPC = "vpc"
    ALB = "alb"
    NLB = "nlb"
    WAF = "waf"
    ROUTE53 = "route53"
    CLOUDFRONT = "cloudfront"
    API_GATEWAY = "api_gateway"
    # AWS Storage
    S3 = "s3"
    EFS = "efs"
    EBS = "ebs"
    # AWS Database
    RDS = "rds"
    AURORA = "aurora"
    DYNAMODB = "dynamodb"
    ELASTICACHE = "elasticache"
    # AWS Integration
    SQS = "sqs"
    SNS = "sns"
    KINESIS = "kinesis"
    # Generic
    GENERIC_COMPUTE = "generic_compute"
    GENERIC_DATABASE = "generic_database"
    GENERIC_STORAGE = "generic_storage"
    CUSTOM = "custom"
    # Non-AWS
    NGINX = "nginx"
    POSTGRESQL = "postgresql"
    OLLAMA = "ollama"
    LANCEDB = "lancedb"


class EdgeStyle(str, Enum):
    """Edge line styles."""
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"


class DiagramNode(BaseModel):
    """A node in the diagram."""
    id: str = Field(..., description="Unique identifier (snake_case)")
    label: str = Field(..., description="Display label")
    node_type: NodeType = Field(..., description="Type of node")
    description: Optional[str] = None
    icon_url: Optional[str] = None


class DiagramEdge(BaseModel):
    """A connection between nodes."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: Optional[str] = None
    style: EdgeStyle = EdgeStyle.SOLID
    bidirectional: bool = False


class DiagramCluster(BaseModel):
    """A grouping of nodes."""
    id: str = Field(..., description="Unique identifier")
    label: str = Field(..., description="Display label")
    node_ids: list[str] = Field(default_factory=list)
    parent_cluster_id: Optional[str] = None


class DiagramSpec(BaseModel):
    """Complete diagram specification."""
    name: str = Field(..., description="Diagram title")
    description: Optional[str] = None
    direction: str = Field(default="TB", description="TB, BT, LR, RL")
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    clusters: list[DiagramCluster] = Field(default_factory=list)


class ClarifyingQuestion(BaseModel):
    """A question to ask for clarification."""
    question: str
    context: str
    options: Optional[list[str]] = None
    default: Optional[str] = None


class ConversationMessage(BaseModel):
    """A message in the conversation."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
