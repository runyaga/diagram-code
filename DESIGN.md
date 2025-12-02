# Design: diagram-as-code

## Overview

This system generates architecture diagrams by:
1. Capturing entities and their relationships in a declarative **SPEC.md** file
2. Using **LLMs** to transform that specification into Python code
3. Executing the code against the [diagrams](https://diagrams.mingrammer.com/) library to produce PNG output

## Core Concept

```
SPEC.md  --(LLM)--> Python code --(diagrams lib)--> PNG
```

The SPEC.md format provides a human-readable, version-controllable way to define architecture:
- **Components**: Named entities with types (e.g., `alb`, `ec2`, `rds`)
- **Connections**: Directed edges between components
- **Clusters**: Logical groupings with optional hierarchy

The LLM's job is to map these declarative definitions to the appropriate `diagrams` library imports and constructs.

## Agent Architecture

The system uses [pydantic-ai](https://ai.pydantic.dev/) agents with typed Pydantic response models. Each agent has a constrained output schema, ensuring the LLM returns structured, validated data.

### Agents

| Agent | Input | Output Model | Purpose |
|-------|-------|--------------|---------|
| **Analyzer** | Natural language description | `AnalysisResponse` | Extracts components, connections, clusters; identifies ambiguities |
| **Generator** | Architecture context | `SpecGenerationResponse` | Produces validated `DiagramSpec` |
| **Refiner** | Feedback + current spec | `SpecRefinementResponse` | Modifies existing spec based on user feedback |

### Generation Process (Structured)

```
1. ANALYZE
   User input --> Analyzer Agent --> AnalysisResponse
                                     - identified_components[]
                                     - identified_connections[]
                                     - suggested_clusters[]
                                     - confidence score
                                     - ready_to_generate flag

2. GENERATE
   AnalysisResponse --> Generator Agent --> SpecGenerationResponse
                                            - DiagramSpec (nodes, edges, clusters)
                                            - explanation
                                            - warnings[]

3. REFINE (optional, iterative)
   User feedback + DiagramSpec --> Refiner Agent --> SpecRefinementResponse
                                                     - understood_changes[]
                                                     - updated DiagramSpec

4. RENDER
   DiagramSpec --> Deterministic Renderer --> Python code --> PNG
```

### Agent Context

All agents share an `AgentContext` that maintains:
- **Conversation history**: Rolling window of user/assistant messages
- **Current spec**: The latest `DiagramSpec` (for refinement)
- **Output path**: Where to write generated artifacts

Agents access context via tools:
- `get_conversation_history()` - Recent conversation for context
- `get_current_spec()` - Current DiagramSpec as JSON (Refiner only)
- `get_available_node_types()` - Valid node type enum values

### Response Models

```python
# Analyzer output
AnalysisResponse:
    summary: str
    identified_components: list[str]
    identified_connections: list[str]
    suggested_clusters: list[str]
    confidence: float  # 0.0-1.0
    ready_to_generate: bool

# Generator output
SpecGenerationResponse:
    spec: DiagramSpec
    explanation: str
    warnings: list[str]

# Refiner output
SpecRefinementResponse:
    understood_changes: list[str]
    updated_spec: DiagramSpec
    explanation: str
```

## Data Model

The intermediate representation (`DiagramSpec`) used by structured generation:

| Model | Fields |
|-------|--------|
| `DiagramSpec` | name, direction, nodes, edges, clusters |
| `DiagramNode` | id, label, node_type |
| `DiagramEdge` | source, target, label |
| `DiagramCluster` | id, label, node_ids, parent_cluster_id |

## Generation Approaches

### Structured (Default)

```
SPEC.md --> Analyzer --> Generator --> DiagramSpec --> Renderer --> Python --> PNG
```

The LLM outputs validated Pydantic models at each step. A deterministic renderer converts the final `DiagramSpec` to Python code. This approach is **constrained but reliable**.

### Direct

```
SPEC.md --> Analyzer --> Code Generator --> Python --> PNG
```

The LLM generates executable Python directly, bypassing the intermediate spec. This is **flexible but variable**—the LLM has full control but may produce invalid code.

## Verification

Optional VLM (Vision Language Model) verification analyzes the generated PNG to confirm components match the specification. This enables automated accuracy measurement for evaluation.

## See Also

- [README.md](README.md) - Installation, usage, and API reference
- [example/SPEC.md](example/SPEC.md) - Complete AWS VPC architecture example
