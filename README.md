# diagram-as-code

Generate architecture diagrams from natural language using LLMs.

## Installation

```bash
pip install -e .
```

**Requires graphviz:**
```bash
brew install graphviz  # macOS
apt install graphviz   # Ubuntu/Debian
```

## Quick Start

```bash
# Interactive mode (recommended)
code-de-diagram

# Direct code generation mode
code-de-diagram --solution direct

# From a spec file
code-de-diagram --spec example/SPEC.md --output ./output
```

## Configuration

Set your LLM provider via environment variables:

```bash
# OpenAI (default)
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o"  # defaults to gpt-4o-mini

# Ollama (local)
export LLM_PROVIDER="ollama"
export OLLAMA_MODEL="qwen3:latest"
export OLLAMA_BASE_URL="http://localhost:11434"
```

## Usage

### Interactive CLI

```
$ code-de-diagram

============================================================
diagram-as-code - Structured Generation
============================================================
Provider: openai | Model: gpt-4o-mini

Describe your architecture. Commands: quit, spec, code, run

You: 3-tier web app with ALB, 2 EC2 instances, and RDS

Analyzing...
Components: ALB, EC2 Instance 1, EC2 Instance 2, RDS Database
Clusters: Web Tier

You: run
SUCCESS: Diagram generated: diagram.png
```

**Commands:**
- `quit` - Exit
- `spec` - Show DiagramSpec as JSON
- `code` - Show generated Python code
- `run` - Generate PNG diagram

### Library Usage

```python
import asyncio
from code_de_diagram import StructuredAgent

async def main():
    agent = StructuredAgent(output_dir="./output")

    analysis = await agent.analyze("""
        RAG system with WAF, 3 NGINX servers,
        PostgreSQL, and Ollama for inference
    """)

    if analysis.ready_to_generate:
        await agent.generate_spec()
        success, message = agent.execute()
        print(message)

asyncio.run(main())
```

### Programmatic Spec Building

```python
from code_de_diagram import (
    DiagramSpec, DiagramNode, DiagramEdge, DiagramCluster,
    NodeType, render_and_execute
)

spec = DiagramSpec(
    name="My Architecture",
    direction="TB",
    nodes=[
        DiagramNode(id="alb", label="Load Balancer", node_type=NodeType.ALB),
        DiagramNode(id="web1", label="Web Server 1", node_type=NodeType.EC2),
        DiagramNode(id="db", label="Database", node_type=NodeType.RDS),
    ],
    edges=[
        DiagramEdge(source="alb", target="web1"),
        DiagramEdge(source="web1", target="db", label="TCP/5432"),
    ],
    clusters=[
        DiagramCluster(id="web_tier", label="Web Tier", node_ids=["web1"]),
    ],
)

success, message, code = render_and_execute(spec, "my_diagram")
```

## Generation Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **Structured** (default) | LLM generates validated `DiagramSpec`, deterministic renderer produces code | Consistent output, easy iteration, schema validation |
| **Direct** | LLM generates executable Python directly | Maximum flexibility, custom layouts |

## Supported Node Types

| Category | Types |
|----------|-------|
| AWS Compute | `ec2`, `lambda`, `ecs`, `eks` |
| AWS Network | `vpc`, `alb`, `nlb`, `waf`, `route53`, `cloudfront`, `api_gateway` |
| AWS Storage | `s3`, `efs`, `ebs` |
| AWS Database | `rds`, `aurora`, `dynamodb`, `elasticache` |
| AWS Integration | `sqs`, `sns`, `kinesis` |
| On-prem | `nginx`, `postgresql`, `generic_compute`, `generic_database` |
| Custom | `ollama`, `lancedb`, `custom` |

## SPEC.md Format

```markdown
# Architecture Title

Description...

## Components
- **id**: Label | node_type | description

## Connections
- source_id -> target_id | label

## Clusters
- **cluster_id**: Label | node_id1, node_id2
- parent: parent_cluster_id
```

See [example/SPEC.md](example/SPEC.md) for a complete example.

## Project Structure

```
code_de_diagram/
├── cli.py           # CLI entry points
├── config.py        # LLM configuration
├── models.py        # Pydantic data models
├── prompts.py       # LLM system prompts
├── renderer.py      # DiagramSpec → Python code
├── spec_parser.py   # SPEC.md file parser
└── solutions/
    ├── direct.py    # Direct code generation
    └── structured.py # Structured spec generation

example/
├── SPEC.md              # Sample architecture spec
├── reference-diagram.png
└── run_evaluation.py    # Compare generation modes
```

## Testing

```bash
pytest tests/ -v
```

## Documentation

See [DESIGN.md](DESIGN.md) for architecture details, system prompts, and data models.

## License

MIT
