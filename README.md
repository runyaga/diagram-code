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
# OpenAI
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o"      # default: gpt-4o

# Ollama (local)
export LLM_PROVIDER="ollama"
export OLLAMA_MODEL="gpt-oss:20b"      # default: gpt-oss:20b
export OLLAMA_VLM_MODEL="qwen3-vl:8b"  # default: qwen3-vl:8b (for VLM verification)
export OLLAMA_BASE_URL="http://localhost:11434"
```

## Usage

### Interactive CLI

```
$ code-de-diagram

============================================================
diagram-as-code - Structured Generation
============================================================
Provider: openai | Model: gpt-4o

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
| **Structured** (default) | LLM generates validated `DiagramSpec`, deterministic renderer produces code | Consistent output, reliable execution, easy iteration |
| **Direct** | LLM generates executable Python directly | Maximum flexibility, custom layouts (may produce errors) |

## SPEC.md Workflow

SPEC.md files are **manually authored** to declaratively describe your target architecture. They serve as both input and ground truth for diagram generation.

### Creating a SPEC.md

1. Start from a reference diagram or architecture description
2. Define components with IDs, labels, and types
3. Define connections between components
4. Define clusters/groupings with hierarchy
5. (Optional) Add expected counts for evaluation

### SPEC.md Format

```markdown
# Architecture Title

Description of the architecture...

## Components
- **node_id**: Label | node_type | description

## Connections
- source_id -> target_id | label

## Clusters
- **cluster_id**: Label | node_id1, node_id2
- parent: parent_cluster_id

## Expected Results
- Total: 10 nodes
- Total: 8 edges
- Total: 3 clusters
```

See [example/SPEC.md](example/SPEC.md) for a complete AWS VPC example.

### Running from SPEC.md

```bash
# Generate diagram using structured approach (default)
code-de-diagram --spec example/SPEC.md --output ./output

# Generate using direct approach
code-de-diagram --spec example/SPEC.md --output ./output --solution direct

# Output results as JSON (for scripting)
code-de-diagram --spec example/SPEC.md --json
```

## Evaluation

Compare both generation approaches against your SPEC.md ground truth:

```bash
# Full evaluation with VLM verification
python example/run_evaluation.py --output example/output

# Skip VLM verification (faster)
python example/run_evaluation.py --output example/output --skip-vlm
```

### Provider-specific Evaluation

```bash
# OpenAI
OPENAI_API_KEY="sk-..." LLM_PROVIDER=openai \
  python example/run_evaluation.py --output example/output-openai

# Ollama
LLM_PROVIDER=ollama OLLAMA_MODEL=gpt-oss:20b OLLAMA_VLM_MODEL=qwen3-vl:8b \
  python example/run_evaluation.py --output example/output-ollama
```

### Evaluation Output

```
example/output/
├── direct/
│   ├── direct_generated.py      # Generated Python code
│   └── diagram.png              # Rendered diagram
├── structured/
│   ├── structured_generated.py  # Generated Python code
│   ├── structured_generated_spec.json  # Intermediate DiagramSpec
│   └── diagram.png              # Rendered diagram
└── evaluation_results.json      # Full comparison metrics
```

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

## Project Structure

```
code_de_diagram/
├── cli.py           # CLI entry points
├── config.py        # LLM configuration (OpenAI/Ollama)
├── models.py        # Pydantic data models
├── prompts.py       # LLM system prompts
├── renderer.py      # DiagramSpec -> Python code
├── spec_parser.py   # SPEC.md file parser
├── vlm_verifier.py  # VLM-based diagram verification
└── solutions/
    ├── direct.py    # Direct code generation
    └── structured.py # Structured spec generation

example/
├── SPEC.md              # Sample AWS VPC architecture spec
├── aws-diagram.png      # Reference diagram
└── run_evaluation.py    # Evaluation runner
```

## Testing

### Install Dev Dependencies

```bash
pip install -e ".[dev]"
# or with uv
uv sync --extra dev
```

### Run All Unit Tests

```bash
pytest tests/ -v -m "not integration"
```

### Run Integration Tests (requires LLM/VLM)

```bash
# All integration tests
pytest tests/ -v -m "integration"

# LLM smoke tests only
pytest tests/test_integration_llm.py -v -m "integration"

# VLM smoke tests only
pytest tests/test_integration_vlm.py -v -m "integration"
```

### Test Categories

| Category | Command | Description |
|----------|---------|-------------|
| Unit | `-m "not integration"` | Fast tests, no network (136 tests) |
| Integration | `-m "integration"` | Requires LLM/VLM services (41 tests) |
| Slow | `-m "integration and slow"` | Actual LLM API calls |

### Test Files

| File | Coverage |
|------|----------|
| `test_config.py` | LLM provider configuration |
| `test_models.py` | Pydantic data models |
| `test_renderer.py` | DiagramSpec to Python code |
| `test_spec_parser.py` | SPEC.md parsing |
| `test_integration_llm.py` | LLM connectivity and smoke tests |
| `test_integration_vlm.py` | VLM analysis and verification |
| `test_solution_direct.py` | DirectGenerationAgent |
| `test_solution_structured.py` | StructuredAgent |
| `test_e2e.py` | End-to-end pipeline |

### Key Smoke Tests

- **`test_ollama_server_reachable`** - Verify Ollama is running
- **`test_analyzer_returns_structured_response`** - Verify LLM returns valid Pydantic models
- **`test_analyze_diagram_returns_analysis`** - Verify VLM can analyze diagram images
- **`test_full_verification_returns_complete_results`** - Full VLM verification pipeline

## Documentation

See [DESIGN.md](DESIGN.md) for architecture details, system prompts, and data models.

## License

MIT
