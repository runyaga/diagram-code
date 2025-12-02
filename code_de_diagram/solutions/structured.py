"""Solution B: Structured Intermediate Representation."""

import os
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from ..models import DiagramSpec, ClarifyingQuestion, ConversationMessage
from ..config import get_model_name
from ..prompts import ANALYZER_PROMPT, SPEC_GENERATOR_PROMPT, REFINER_SPEC_PROMPT
from ..renderer import render_spec_to_code, render_and_execute


class AnalysisResponse(BaseModel):
    """Analysis of user input."""
    summary: str
    identified_components: list[str]
    identified_connections: list[str]
    suggested_clusters: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    questions: list[ClarifyingQuestion] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    ready_to_generate: bool


class SpecGenerationResponse(BaseModel):
    """Generated diagram specification."""
    spec: DiagramSpec
    explanation: str
    warnings: list[str] = Field(default_factory=list)


class SpecRefinementResponse(BaseModel):
    """Refined specification response."""
    understood_changes: list[str]
    updated_spec: DiagramSpec
    explanation: str


@dataclass
class AgentContext:
    """Agent context."""
    conversation_history: list[ConversationMessage] = field(default_factory=list)
    current_spec: Optional[DiagramSpec] = None
    output_path: str = "diagram"


_analyzer: Optional[Agent] = None
_generator: Optional[Agent] = None
_refiner: Optional[Agent] = None


def _get_history(ctx: RunContext[AgentContext]) -> str:
    if not ctx.deps.conversation_history:
        return "No previous conversation."
    return "\n".join(f"{m.role.upper()}: {m.content}" for m in ctx.deps.conversation_history[-10:])


def _get_node_types(ctx: RunContext[AgentContext]) -> str:
    return """Available NodeType values:
AWS Compute: ec2, lambda, ecs, eks
AWS Network: vpc, alb, nlb, waf, route53, cloudfront, api_gateway
AWS Storage: s3, efs, ebs
AWS Database: rds, aurora, dynamodb, elasticache
AWS Integration: sqs, sns, kinesis
On-prem/Generic: nginx, postgresql, generic_compute, generic_database, generic_storage
Custom: ollama, lancedb, custom"""


def get_analyzer() -> Agent:
    global _analyzer
    if _analyzer is None:
        _analyzer = Agent(get_model_name(), output_type=AnalysisResponse,
                          system_prompt=ANALYZER_PROMPT, deps_type=AgentContext)
        @_analyzer.tool
        async def get_conversation_history(ctx: RunContext[AgentContext]) -> str:
            return _get_history(ctx)
    return _analyzer


def get_generator() -> Agent:
    global _generator
    if _generator is None:
        _generator = Agent(get_model_name(), output_type=SpecGenerationResponse,
                           system_prompt=SPEC_GENERATOR_PROMPT, deps_type=AgentContext)
        @_generator.tool
        async def get_conversation_history(ctx: RunContext[AgentContext]) -> str:
            return _get_history(ctx)
        @_generator.tool
        async def get_available_node_types(ctx: RunContext[AgentContext]) -> str:
            return _get_node_types(ctx)
    return _generator


def get_refiner() -> Agent:
    global _refiner
    if _refiner is None:
        _refiner = Agent(get_model_name(), output_type=SpecRefinementResponse,
                         system_prompt=REFINER_SPEC_PROMPT, deps_type=AgentContext)
        @_refiner.tool
        async def get_conversation_history(ctx: RunContext[AgentContext]) -> str:
            return _get_history(ctx)
        @_refiner.tool
        async def get_current_spec(ctx: RunContext[AgentContext]) -> str:
            if ctx.deps.current_spec:
                return ctx.deps.current_spec.model_dump_json(indent=2)
            return "No spec generated yet."
        @_refiner.tool
        async def get_available_node_types(ctx: RunContext[AgentContext]) -> str:
            return _get_node_types(ctx)
    return _refiner


class StructuredAgent:
    """Structured diagram generation agent."""

    def __init__(self, output_dir: str = "."):
        self.context = AgentContext(output_path=os.path.join(output_dir, "diagram"))
        self.current_spec: Optional[DiagramSpec] = None
        self.generated_code: Optional[str] = None
        self.diagram_path: Optional[str] = None

    def _add_message(self, role: str, content: str):
        self.context.conversation_history.append(ConversationMessage(role=role, content=content))

    async def analyze(self, user_input: str) -> AnalysisResponse:
        """Analyze user input."""
        self._add_message("user", user_input)
        result = await get_analyzer().run(
            f"Analyze this architecture description:\n\n{user_input}",
            deps=self.context
        )
        self._add_message("assistant", f"Analysis: {result.output.summary}")
        return result.output

    async def generate_spec(self, architecture_description: str = "") -> SpecGenerationResponse:
        """Generate diagram specification.

        Args:
            architecture_description: Full description of the architecture to generate.
                                     If not provided, uses conversation history.
        """
        # Build the prompt with full architecture context
        prompt_parts = ["Generate a DiagramSpec for this architecture."]

        if architecture_description:
            prompt_parts.append(f"\nARCHITECTURE SPECIFICATION:\n{architecture_description}")
        else:
            # Fallback to conversation history
            history = "\n".join(
                f"{m.role.upper()}: {m.content}"
                for m in self.context.conversation_history[-5:]
            )
            prompt_parts.append(f"\nCONVERSATION CONTEXT:\n{history}")

        result = await get_generator().run(
            "\n".join(prompt_parts),
            deps=self.context
        )
        self.current_spec = result.output.spec
        self.context.current_spec = self.current_spec
        self._add_message("assistant", f"Generated spec: {result.output.explanation}")
        return result.output

    async def refine_spec(self, feedback: str) -> SpecRefinementResponse:
        """Refine the specification."""
        self._add_message("user", f"Feedback: {feedback}")
        result = await get_refiner().run(f"Modify the diagram:\n\n{feedback}", deps=self.context)
        self.current_spec = result.output.updated_spec
        self.context.current_spec = self.current_spec
        self._add_message("assistant", f"Refined: {result.output.explanation}")
        return result.output

    def render_code(self) -> str:
        """Render spec to Python code."""
        if not self.current_spec:
            raise ValueError("No spec generated yet")
        self.generated_code = render_spec_to_code(self.current_spec, self.context.output_path)
        return self.generated_code

    def execute(self) -> tuple[bool, str]:
        """Execute to produce diagram."""
        if not self.current_spec:
            return False, "No spec generated yet"
        success, message, code = render_and_execute(self.current_spec, self.context.output_path)
        self.generated_code = code
        if success:
            self.diagram_path = f"{self.context.output_path}.png"
        return success, message

    def get_spec(self) -> Optional[DiagramSpec]:
        return self.current_spec

    def get_spec_json(self) -> Optional[str]:
        return self.current_spec.model_dump_json(indent=2) if self.current_spec else None

    def get_code(self) -> Optional[str]:
        return self.generated_code

    def get_diagram_path(self) -> Optional[str]:
        return self.diagram_path

    def load_spec_from_json(self, json_str: str):
        """Load spec from JSON."""
        self.current_spec = DiagramSpec.model_validate_json(json_str)
        self.context.current_spec = self.current_spec
