"""Shared data structures for the pipeline."""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ASTArgument:
    name: str
    type: str
    required: bool = True


@dataclass
class ASTQuery:
    name: str
    sql: str
    tables: list[str]
    operation: str  # SELECT, INSERT, UPDATE, DELETE
    params: list[dict] = field(default_factory=list)
    parameterized: bool = True


@dataclass
class ASTScopeWrite:
    scope: str  # session, application, variables
    key: str
    value: str = ""


@dataclass
class ASTConditional:
    condition: str
    action: str  # throw, return, set, etc.
    detail: str = ""


@dataclass
class ASTFunctionCall:
    target: str
    args: list[str] = field(default_factory=list)


@dataclass
class ASTFunction:
    name: str
    access: str  # public, private
    return_type: str
    arguments: list[ASTArgument] = field(default_factory=list)
    queries: list[ASTQuery] = field(default_factory=list)
    scope_writes: list[ASTScopeWrite] = field(default_factory=list)
    conditionals: list[ASTConditional] = field(default_factory=list)
    function_calls: list[ASTFunctionCall] = field(default_factory=list)
    returns: dict = field(default_factory=dict)


@dataclass
class ASTComponent:
    name: str
    file: str
    type: str  # component, template
    extends: str = ""
    properties: list[dict] = field(default_factory=list)
    functions: list[ASTFunction] = field(default_factory=list)


@dataclass
class BusinessRule:
    name: str
    description: str
    source: str = "ai"  # "ai" or "deterministic" or "human"
    confidence: int = 90


@dataclass
class SemanticFunction:
    name: str
    signature: dict
    business_rule: BusinessRule
    data_access: list[dict] = field(default_factory=list)
    state_writes: list[dict] = field(default_factory=list)
    control_flow: list[dict] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    called_by: list[str] = field(default_factory=list)


@dataclass
class SemanticModule:
    module: str
    source: str
    functions: list[SemanticFunction] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    complexity: str = "low"  # low, medium, high
    approved: bool = False
    approved_by: Optional[str] = None


def to_dict(obj):
    """Convert dataclass to dict recursively."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return obj
