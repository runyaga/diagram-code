"""Solution A: Direct LLM Code Generation."""

import os
import sys
import tempfile
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from ..models import ClarifyingQuestion, ConversationMessage
from ..config import get_model_name
from ..prompts import ANALYZER_PROMPT, CODE_GENERATOR_PROMPT, REFINER_PROMPT


class AnalysisResponse(BaseModel):
    """Analysis of user input."""
    summary: str
    identified_components: list[str]
    identified_connections: list[str]
    ambiguities: list[str] = Field(default_factory=list)
    questions: list[ClarifyingQuestion] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    ready_to_generate: bool


class CodeGenerationResponse(BaseModel):
    """Generated diagram code."""
    python_code: str
    explanation: str
    warnings: list[str] = Field(default_factory=list)


class RefinementResponse(BaseModel):
    """Refined code response."""
    understood_changes: list[str]
    updated_code: str
    explanation: str


@dataclass
class AgentContext:
    """Agent context."""
    conversation_history: list[ConversationMessage] = field(default_factory=list)
    current_code: Optional[str] = None
    output_path: str = "diagram"


_analyzer: Optional[Agent] = None
_generator: Optional[Agent] = None
_refiner: Optional[Agent] = None


def _get_history(ctx: RunContext[AgentContext]) -> str:
    if not ctx.deps.conversation_history:
        return "No previous conversation."
    return "\n".join(f"{m.role.upper()}: {m.content}" for m in ctx.deps.conversation_history[-10:])


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
        _generator = Agent(get_model_name(), output_type=CodeGenerationResponse,
                           system_prompt=CODE_GENERATOR_PROMPT, deps_type=AgentContext)
        @_generator.tool
        async def get_conversation_history(ctx: RunContext[AgentContext]) -> str:
            return _get_history(ctx)
    return _generator


def get_refiner() -> Agent:
    global _refiner
    if _refiner is None:
        _refiner = Agent(get_model_name(), output_type=RefinementResponse,
                         system_prompt=REFINER_PROMPT, deps_type=AgentContext)
        @_refiner.tool
        async def get_conversation_history(ctx: RunContext[AgentContext]) -> str:
            return _get_history(ctx)
        @_refiner.tool
        async def get_current_code(ctx: RunContext[AgentContext]) -> str:
            return ctx.deps.current_code or "No code generated yet."
    return _refiner


class DirectGenerationAgent:
    """Direct LLM code generation agent."""

    def __init__(self, output_dir: str = "."):
        self.context = AgentContext(output_path=os.path.join(output_dir, "diagram"))
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

    async def generate_code(self, architecture_description: str = "") -> CodeGenerationResponse:
        """Generate diagram code.

        Args:
            architecture_description: Full description of the architecture to generate.
                                     If not provided, uses conversation history.
        """
        # Build the prompt with full architecture context
        prompt_parts = [
            f"Generate Python diagram code for this architecture.",
            f"Output filename: {os.path.basename(self.context.output_path)}",
        ]

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
        self.generated_code = result.output.python_code
        self.context.current_code = self.generated_code
        self._add_message("assistant", f"Generated: {result.output.explanation}")
        return result.output

    async def refine(self, feedback: str) -> RefinementResponse:
        """Refine generated code."""
        self._add_message("user", f"Feedback: {feedback}")
        result = await get_refiner().run(f"Modify the diagram:\n\n{feedback}", deps=self.context)
        self.generated_code = result.output.updated_code
        self.context.current_code = self.generated_code
        self._add_message("assistant", f"Refined: {result.output.explanation}")
        return result.output

    def execute_code(self) -> tuple[bool, str]:
        """Execute the generated code."""
        if not self.generated_code:
            return False, "No code generated yet"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(self.generated_code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True, text=True, timeout=60,
                cwd=os.path.dirname(self.context.output_path) or "."
            )
            if result.returncode == 0:
                for path in [f"{self.context.output_path}.png", f"{os.path.basename(self.context.output_path)}.png"]:
                    if os.path.exists(path):
                        self.diagram_path = path
                        return True, f"Diagram generated: {path}"
                return True, f"Executed: {result.stdout}"
            return False, f"Failed:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)
        finally:
            os.unlink(temp_path)

    def get_code(self) -> Optional[str]:
        return self.generated_code

    def get_diagram_path(self) -> Optional[str]:
        return self.diagram_path
