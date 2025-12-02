# Example: AWS Production VPC Architecture

This directory contains an example demonstrating how to use code.de.diagram with a multi-AZ AWS production architecture.

## Contents

| File | Description |
|------|-------------|
| `aws-diagram.png` | Original reference diagram showing the target architecture |
| `SPEC.md` | Declarative specification of the architecture (manually authored) |
| `run_evaluation.py` | Evaluation script comparing both generation approaches |

## Architecture Overview

The diagram represents a production-ready AWS infrastructure with:

- **Multi-AZ Design**: Two availability zones for high availability
- **Three-tier Subnets**: Public, Application (private), and Database (private) tiers
- **Auto Scaling**: Web and application tier EC2 instances in auto scaling groups
- **NAT Gateways**: Outbound internet access for private subnets
- **Aurora Databases**: Multi-AZ database deployment
- **Security Controls**: WAF, Network ACLs, and IAM

## Quick Start

### Prerequisites

```bash
# From project root
pip install -e .

# Ensure LLM provider is configured
export LLM_PROVIDER="ollama"  # or set OPENAI_API_KEY for OpenAI
```

### Run Evaluation

```bash
# From project root - full evaluation with VLM verification
python example/run_evaluation.py

# Skip VLM verification (faster)
python example/run_evaluation.py --skip-vlm

# Custom output directory
python example/run_evaluation.py --output example/output-test
```

### Provider-specific Runs

```bash
# OpenAI (gpt-4o)
OPENAI_API_KEY="sk-..." LLM_PROVIDER=openai \
  python example/run_evaluation.py --output example/output-openai

# Ollama (gpt-oss:20b + qwen3-vl:8b for VLM)
LLM_PROVIDER=ollama OLLAMA_MODEL=gpt-oss:20b OLLAMA_VLM_MODEL=qwen3-vl:8b \
  python example/run_evaluation.py --output example/output-ollama
```

### CLI Non-Interactive Mode

```bash
# Run structured solution (default)
code-de-diagram --spec example/SPEC.md --output ./output

# Run direct solution
code-de-diagram --spec example/SPEC.md --output ./output --solution direct

# Output as JSON (for scripting)
code-de-diagram --spec example/SPEC.md --json
```

## About SPEC.md

The `SPEC.md` file is **manually authored** to describe the target architecture. It serves as:

1. **Input**: The LLM reads the spec to understand what diagram to generate
2. **Ground Truth**: The evaluation compares generated output against spec counts

### Writing Your Own SPEC.md

Start from a reference diagram or architecture description, then define:

1. **Components** with unique IDs, labels, and node types
2. **Connections** between components with optional labels
3. **Clusters** for logical groupings (supports nesting via `parent:`)
4. **Expected Results** for evaluation metrics

See `SPEC.md` in this directory for a complete example.

## Expected Results

From the SPEC.md Expected Results section:
- 22 nodes total
- 13 connections
- 13 clusters (with nested hierarchy)

## Output Structure

After running evaluation:

```
output/
├── direct/
│   ├── direct_generated.py      # Generated Python code
│   └── diagram.png              # Rendered diagram (if successful)
├── structured/
│   ├── structured_generated.py  # Generated Python code
│   ├── structured_generated_spec.json  # Intermediate DiagramSpec
│   └── diagram.png              # Rendered diagram (if successful)
└── evaluation_results.json      # Full comparison metrics
```

## Evaluation Metrics

The evaluation measures:

1. **Count Accuracy**: Compares generated node/edge/cluster counts vs ground truth
2. **VLM Verification**: Uses a vision model to analyze the generated PNG and verify components are correctly rendered

### Sample Results

| Provider | Approach | Node Acc | Edge Acc | Cluster Acc | Diagram |
|----------|----------|----------|----------|-------------|---------|
| OpenAI | Structured | 100% | 85% | 85% | Success |
| OpenAI | Direct | 100% | 185% | 100% | Failed |
| Ollama | Structured | 109% | 162% | 62% | Success |
| Ollama | Direct | 109% | 169% | 85% | Success |

> Accuracy >100% means over-generation (more items than expected)
