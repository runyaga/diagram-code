# DESIGN: diagram-as-code

LLM-driven architecture diagram generation using the Python [diagrams](https://diagrams.mingrammer.com/) library.

## Architecture

```
User Input                    SPEC.md File
(natural language)            (declarative)
      |                            |
      v                            v
+--------------+              +-----------+
|   Analyzer   |              |  Parser   |
+------+-------+              +-----+-----+
       |                            |
       +------------+---------------+
                    v
            +--------------+
            |  Generator   |
            +-------+------+
                    |
       +------------+------------+
       v                         v
   Direct (A)              Structured (B)
   Python Code             DiagramSpec -> Renderer
       |                         |
       +-----------+-------------+
                   v
              PNG Diagram
                   |
                   v
           +--------------+
           | VLM Verifier |  (optional)
           +--------------+
```

## Generation Modes

| Mode | Flow | Trade-off |
|------|------|-----------|
| **Direct** | LLM -> Python code -> PNG | Flexible but variable output, may produce syntax errors |
| **Structured** | LLM -> DiagramSpec -> Renderer -> PNG | Constrained but deterministic, more reliable execution |

## Data Model

```python
class DiagramSpec:
    name: str                    # Diagram title
    direction: str               # TB, BT, LR, RL
    nodes: list[DiagramNode]     # id, label, node_type
    edges: list[DiagramEdge]     # source, target, label
    clusters: list[DiagramCluster]  # id, label, node_ids, parent_cluster_id
```

## Node Types -> Diagrams Library

| NodeType | Import |
|----------|--------|
| `ec2`, `lambda`, `ecs`, `eks` | `diagrams.aws.compute.*` |
| `alb`, `nlb`, `waf`, `route53` | `diagrams.aws.network.*` / `security.*` |
| `s3`, `efs`, `ebs` | `diagrams.aws.storage.*` |
| `rds`, `aurora`, `dynamodb`, `elasticache` | `diagrams.aws.database.*` |
| `nginx` | `diagrams.onprem.network.Nginx` |
| `postgresql` | `diagrams.onprem.database.PostgreSQL` |
| `ollama`, `lancedb`, `custom` | `diagrams.onprem.compute.Server` |

## SPEC.md Format

Declarative markdown format for non-interactive mode. SPEC.md files are **manually authored** to describe your target architecture:

```markdown
# Title

Description of the architecture...

## Components
- **node_id**: Label | node_type | description

## Connections
- source_id -> target_id | label

## Clusters
- **cluster_id**: Label | node_id1, node_id2
- parent: parent_cluster_id

## Expected Results
- Total: N nodes
- (optional ground truth counts for evaluation)
```

## Evaluation

Two-level accuracy measurement:

1. **Count-based**: Compare generated node/edge/cluster counts against SPEC.md
2. **VLM-based**: Analyze generated PNG with vision model to verify correct components rendered

```bash
python example/run_evaluation.py              # Full evaluation with VLM
python example/run_evaluation.py --skip-vlm   # Count-only (faster)
```

### Provider Configuration

```bash
# OpenAI
LLM_PROVIDER=openai OPENAI_API_KEY="sk-..." python example/run_evaluation.py

# Ollama (local)
LLM_PROVIDER=ollama OLLAMA_MODEL=gpt-oss:20b OLLAMA_VLM_MODEL=qwen3-vl:8b python example/run_evaluation.py
```

## Key Files

| File | Purpose |
|------|---------|
| `prompts.py` | LLM system prompts for analyzer, generator, refiner |
| `models.py` | Pydantic models: DiagramSpec, DiagramNode, DiagramEdge, DiagramCluster |
| `renderer.py` | DiagramSpec -> Python code (deterministic) |
| `spec_parser.py` | SPEC.md -> DiagramSpec |
| `vlm_verifier.py` | PNG diagram analysis and verification |
| `solutions/direct.py` | Direct code generation agent |
| `solutions/structured.py` | Structured spec generation agent |
| `config.py` | LLM provider configuration (OpenAI/Ollama) |
