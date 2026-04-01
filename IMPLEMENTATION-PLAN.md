# Implementation Plan — Modernize CLI (v2)

> **Audience**: An AI coding assistant (Sonnet 4.5 or equivalent) that will implement this plan step by step.
> **Source of truth**: `DESIGN-v2.md` and `DESIGN.md` in this repo. This plan translates those designs into exact code specifications.
> **Reference implementation**: `mock_tool/` contains a working demo with mock data. Use it to understand the UX, data shapes, and CLI flow — but do NOT copy its code. The production tool replaces mock data with real logic.

---

## Table of Contents

1. [Project Setup & Directory Structure](#1-project-setup--directory-structure)
2. [Dependencies](#2-dependencies)
3. [Coding Conventions & Patterns](#3-coding-conventions--patterns)
4. [Data Models (Core Types)](#4-data-models-core-types)
5. [Phase 1: Foundation + Core Engine](#5-phase-1-foundation--core-engine)
6. [Phase 2: Parser + Extractor + ColdFusion Adapter](#6-phase-2-parser--extractor--coldfusion-adapter)
7. [Phase 3: Lock Manager + Architect Module](#7-phase-3-lock-manager--architect-module)
8. [Phase 4: Generator Module + React/Go Adapters](#8-phase-4-generator-module--reactgo-adapters)
9. [Phase 5: Verifier Module](#9-phase-5-verifier-module)
10. [Phase 6: Polish + Auto Mode](#10-phase-6-polish--auto-mode)
11. [Testing Strategy](#11-testing-strategy)
12. [Error Handling Contract](#12-error-handling-contract)
13. [Implementation Order Within Each Phase](#13-implementation-order-within-each-phase)

---

## 1. Project Setup & Directory Structure

Create a new directory `app/` at the repo root. This is the production codebase.

```
app/
├── modernize.py                    # CLI entry point (Click group)
├── requirements.txt                # All dependencies with pinned versions
├── pytest.ini                      # pytest configuration
├── README.md                       # Setup + usage (copy CLI workflow from DESIGN-v2.md)
│
├── core/                           # Core engine — language-agnostic infrastructure
│   ├── __init__.py
│   ├── models.py                   # All dataclasses (AST nodes, semantic model, locks)
│   ├── state.py                    # ProjectState — .modernize/ directory management
│   ├── schemas.py                  # JSON Schema definitions for validation
│   ├── sanitizer.py                # Data redaction engine
│   ├── chunker.py                  # AST-node-level chunking for context windows
│   ├── context_assembler.py        # Build context packets for AI calls
│   ├── aggregator.py               # Merge multi-chunk AI results
│   ├── audit.py                    # AI call audit logging
│   └── errors.py                   # Custom exception hierarchy
│
├── providers/                      # AI provider adapters
│   ├── __init__.py
│   ├── base.py                     # Abstract AIProvider interface
│   ├── claude.py                   # Anthropic Claude adapter
│   ├── openai_provider.py          # OpenAI adapter (name avoids shadowing `openai` package)
│   └── gemini.py                   # Google Gemini adapter
│
├── pipeline/                       # Pipeline stage modules
│   ├── __init__.py
│   ├── parser.py                   # Step 1: Parse to AST
│   ├── extractor.py                # Step 2: Extract semantics
│   ├── documenter.py               # Step 3: Generate review docs
│   ├── reviewer.py                 # Step 4: Interactive review
│   ├── locker.py                   # Step 5a/5d: Lock mappings
│   ├── architect.py                # Step 5b: Design architecture
│   ├── generator.py                # Step 6: Generate code
│   ├── verifier.py                 # Step 7: Verify equivalence
│   └── runner.py                   # Auto mode: run full pipeline
│
├── adapters/                       # Language-specific adapters
│   ├── __init__.py
│   ├── source/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract SourceAdapter interface
│   │   └── coldfusion/
│   │       ├── __init__.py
│   │       ├── adapter.py          # ColdFusionAdapter — implements SourceAdapter
│   │       ├── parser.py           # tree-sitter walker → semantic AST
│   │       ├── sql_extractor.py    # SQL string parsing (uses sqlglot)
│   │       └── agents/             # Agent definition YAML files
│   │           ├── cf-logic-agent.yaml
│   │           ├── cf-query-agent.yaml
│   │           ├── cf-ui-agent.yaml
│   │           ├── cf-auth-agent.yaml
│   │           ├── cf-form-agent.yaml
│   │           ├── cf-task-agent.yaml
│   │           └── cf-email-agent.yaml
│   └── target/
│       ├── __init__.py
│       ├── base.py                 # Abstract TargetAdapter interface
│       ├── react/
│       │   ├── __init__.py
│       │   ├── adapter.py          # ReactAdapter — implements TargetAdapter
│       │   ├── scaffolder.py       # Vite + React project setup
│       │   └── conventions.py      # React conventions as structured data
│       └── go/
│           ├── __init__.py
│           ├── adapter.py          # GoAdapter — implements TargetAdapter
│           ├── scaffolder.py       # Go module + Chi router setup
│           └── conventions.py      # Go conventions as structured data
│
├── agents/                         # Agent system
│   ├── __init__.py
│   ├── loader.py                   # Load agent YAML definitions
│   ├── resolver.py                 # Match AST nodes → agents via appliesTo rules
│   └── registry.py                 # Global registry of loaded agents
│
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Shared fixtures (tmp dirs, sample ASTs, mock providers)
    ├── unit/
    │   ├── __init__.py
    │   ├── test_models.py
    │   ├── test_state.py
    │   ├── test_sanitizer.py
    │   ├── test_chunker.py
    │   ├── test_context_assembler.py
    │   ├── test_aggregator.py
    │   ├── test_audit.py
    │   ├── test_locker.py
    │   ├── test_agent_loader.py
    │   ├── test_agent_resolver.py
    │   └── test_sql_extractor.py
    ├── integration/
    │   ├── __init__.py
    │   ├── test_cf_parser.py       # ColdFusion adapter end-to-end
    │   ├── test_pipeline_flow.py   # Full pipeline from parse → verify
    │   └── test_cli.py             # Click CLI integration tests
    └── fixtures/
        ├── sample_cf/              # Copy of mock_tool/sample_app/ CF files
        │   ├── UserService.cfc
        │   ├── OrderService.cfc
        │   └── login.cfm
        ├── expected_ast/           # Expected AST JSON output for each CF file
        │   ├── UserService.cfc.ast.json
        │   ├── OrderService.cfc.ast.json
        │   └── login.cfm.ast.json
        └── expected_semantics/     # Expected semantic JSON for each module
            ├── UserService.semantic.json
            ├── OrderService.semantic.json
            └── login.semantic.json
```

### Files that should NOT be created

- No `setup.py` or `pyproject.toml` — use `requirements.txt` only
- No `Makefile` — keep it simple
- No Docker files — local-first tool
- No `.env` files — API keys are passed via CLI options or environment variables

---

## 2. Dependencies

Create `app/requirements.txt` with these exact dependencies:

```
# CLI + terminal UI
click>=8.1,<9.0
rich>=13.0,<14.0

# AI providers
anthropic>=0.40,<1.0
openai>=1.50,<2.0
google-genai>=1.0,<2.0

# Parsing
tree-sitter>=0.24,<1.0
tree-sitter-cfml>=0.1.0
sqlglot>=26.0,<27.0

# Utilities
pyyaml>=6.0,<7.0
jsonschema>=4.20,<5.0

# Testing (dev)
pytest>=8.0,<9.0
pytest-tmp-files>=0.0.2
```

**Important notes on dependencies:**

- `tree-sitter-cfml`: If this package does not exist on PyPI at implementation time, you must write a fallback regex-based ColdFusion parser in `adapters/source/coldfusion/parser.py` that handles the tag-based syntax (`<cffunction>`, `<cfquery>`, `<cfset>`, `<cfif>`, `<cfargument>`, `<cfreturn>`, `<cfcomponent>`, `<cfloop>`, `<cftry>/<cfcatch>`, `<cftransaction>`, `<cflocation>`, `<cfmail>`, `<cfschedule>`). This is acceptable because ColdFusion's XML-like tag syntax is regular enough for deterministic regex parsing. Use `re` module with named groups. See Phase 2 for detailed parser specification.
- `google-genai`: This is Google's new unified SDK. If import issues arise, use `google-generativeai` instead.
- All AI provider packages are imported lazily — only when the user selects that provider. Do NOT import them at module level. This prevents import errors when a user only has one provider's SDK installed.

---

## 3. Coding Conventions & Patterns

**Follow these conventions strictly. They are non-negotiable.**

### 3.1 Type Hints

Every function must have full type annotations. Use `from __future__ import annotations` at the top of every `.py` file.

```python
from __future__ import annotations

def extract_semantics(ast: ASTComponent, provider: AIProvider | None = None) -> SemanticModule:
    ...
```

### 3.2 Dataclasses for All Data Models

All data structures use `@dataclass`. No TypedDicts, no plain dicts (except for JSON serialization at the boundary). No Pydantic.

```python
from dataclasses import dataclass, field

@dataclass
class ASTQuery:
    name: str
    sql: str
    tables: list[str]
    operation: str  # "SELECT" | "INSERT" | "UPDATE" | "DELETE"
    params: list[ASTParam] = field(default_factory=list)
    parameterized: bool = True
```

### 3.3 Serialization Pattern

Every dataclass must have `to_dict()` and `from_dict()` class methods. Do NOT use `dataclasses.asdict()` because it doesn't handle nested objects with custom serialization.

```python
@dataclass
class ASTQuery:
    name: str
    sql: str
    tables: list[str]
    # ...

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "sql": self.sql,
            "tables": self.tables,
            # ... all fields
        }

    @classmethod
    def from_dict(cls, data: dict) -> ASTQuery:
        return cls(
            name=data["name"],
            sql=data["sql"],
            tables=data["tables"],
            # ... all fields
        )
```

### 3.4 Error Handling Pattern

Use a custom exception hierarchy (defined in `core/errors.py`). Never use bare `Exception`. Never silently swallow exceptions.

```python
class ModernizeError(Exception):
    """Base exception for all modernize errors."""
    pass

class PipelineError(ModernizeError):
    """Error during pipeline execution."""
    def __init__(self, step: str, message: str):
        self.step = step
        super().__init__(f"[{step}] {message}")

class StateError(ModernizeError):
    """Error with .modernize/ state."""
    pass

class AdapterError(ModernizeError):
    """Error in a source/target adapter."""
    pass

class ProviderError(ModernizeError):
    """Error communicating with AI provider."""
    def __init__(self, provider: str, message: str, retryable: bool = False):
        self.provider = provider
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")

class LockError(ModernizeError):
    """Error with lock integrity."""
    pass

class ValidationError(ModernizeError):
    """Schema or data validation error."""
    pass
```

### 3.5 Console Output Pattern

All user-facing output uses `rich`. Create a shared console instance in `core/__init__.py`:

```python
# core/__init__.py
from rich.console import Console
console = Console()
```

Import this everywhere: `from core import console`. Do NOT create multiple Console instances.

### 3.6 Abstract Base Classes for Interfaces

Use Python's `abc.ABC` and `@abstractmethod` for all plugin interfaces:

```python
from abc import ABC, abstractmethod

class SourceAdapter(ABC):
    @abstractmethod
    def detect(self, files: list[str]) -> bool: ...

    @abstractmethod
    def parse_to_ast(self, file_path: str) -> ASTComponent: ...
```

### 3.7 No Global Mutable State

All state flows through function arguments. No module-level mutable variables. The only exception is the shared `console` instance (which is stateless output).

### 3.8 File I/O Pattern

All file reads/writes go through `ProjectState`. No direct `open()` calls in pipeline modules. Exception: adapter code reading source files during parsing.

---

## 4. Data Models (Core Types)

File: `app/core/models.py`

This is the most critical file. Every downstream module depends on these types. Get them right.

### 4.1 AST Models (Step 1 output)

```python
@dataclass
class ASTParam:
    value: str                      # "arguments.email", "now()", literal values
    type: str                       # "cf_sql_varchar", "cf_sql_integer", etc.

@dataclass
class ASTQuery:
    name: str                       # "qUser", "(inline)" for unnamed queries
    sql: str                        # Full SQL string
    tables: list[str]               # Tables referenced (extracted from SQL)
    operation: str                  # "SELECT" | "INSERT" | "UPDATE" | "DELETE"
    params: list[ASTParam] = field(default_factory=list)
    parameterized: bool = True      # Uses parameterized queries?

@dataclass
class ASTArgument:
    name: str
    type: str                       # "string", "numeric", "array", "struct", "query", "boolean", "any"
    required: bool = True
    default: str | None = None

@dataclass
class ASTScopeWrite:
    scope: str                      # "session", "application", "variables", "request", "form"
    key: str                        # "userId", "userRole", etc.
    value: str = ""                 # The value expression

@dataclass
class ASTConditional:
    condition: str                  # Human-readable condition description
    action: str                     # "throw", "return", "set", "redirect", "process_form"
    detail: str = ""                # Additional context (error type, redirect target)

@dataclass
class ASTFunctionCall:
    target: str                     # "hashVerify", "userService.authenticate", "createObject"
    args: list[str] = field(default_factory=list)

@dataclass
class ASTFunction:
    name: str                       # "(page_logic)" for template-level code
    access: str                     # "public", "private", "remote", "package"
    return_type: str                # "struct", "query", "void", "numeric", "string", "boolean", "any"
    arguments: list[ASTArgument] = field(default_factory=list)
    queries: list[ASTQuery] = field(default_factory=list)
    scope_writes: list[ASTScopeWrite] = field(default_factory=list)
    conditionals: list[ASTConditional] = field(default_factory=list)
    function_calls: list[ASTFunctionCall] = field(default_factory=list)
    returns: dict = field(default_factory=dict)  # {"type": "struct", "keys": [...]} or {"type": "query", "columns": [...]}
    transactional: bool = False     # Wrapped in <cftransaction>?

    # Serialization methods: to_dict(), from_dict()

@dataclass
class ASTProperty:
    name: str
    type: str
    scope: str                      # "variables", "this"
    value: str = ""                 # Default value expression

@dataclass
class ASTComponent:
    name: str                       # "UserService", "login"
    file: str                       # "UserService.cfc", "login.cfm"
    type: str                       # "component" (CFC) or "template" (CFM)
    extends: str = ""               # Parent component name
    properties: list[ASTProperty] = field(default_factory=list)
    functions: list[ASTFunction] = field(default_factory=list)

    # Serialization methods: to_dict(), from_dict()
```

### 4.2 Semantic Models (Step 2 output)

```python
@dataclass
class BusinessRule:
    name: str                       # "User Authentication"
    description: str                # Full description of the business rule
    source: str                     # "ai" | "deterministic" | "human"
    confidence: int = 90            # 0-100

@dataclass
class DataAccess:
    table: str
    operation: str                  # "SELECT" | "INSERT" | "UPDATE" | "DELETE"
    columns: list[str] = field(default_factory=list)
    filter: str = ""                # "email = ?" or ""
    purpose: str = ""               # "Check for duplicate email"
    parameterized: bool = True

@dataclass
class StateWrite:
    scope: str
    key: str
    condition: str = ""             # "only if email changed", or "" for unconditional

@dataclass
class ControlFlowRule:
    condition: str                  # "no user found"
    action: str                     # "throw InvalidCredentials"

@dataclass
class SemanticFunction:
    name: str
    signature: dict                 # {"inputs": [...], "outputs": {...}}
    business_rule: BusinessRule
    data_access: list[DataAccess] = field(default_factory=list)
    state_writes: list[StateWrite] = field(default_factory=list)
    control_flow: list[ControlFlowRule] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    called_by: list[str] = field(default_factory=list)
    transactional: bool = False

    # Serialization: to_dict() / from_dict()
    # IMPORTANT: to_dict() must output keys in camelCase for JSON
    # (businessRule, dataAccess, stateWrites, controlFlow, calledBy)

@dataclass
class UIElements:
    """Only present for template-type modules (CFM pages)."""
    form: dict | None = None        # {"action": "/login.cfm", "method": "post", "fields": [...]}
    links: list[str] = field(default_factory=list)
    error_display: str = ""         # "conditional banner", "inline", etc.

@dataclass
class SemanticModule:
    module: str                     # "UserService"
    source: str                     # "UserService.cfc"
    functions: list[SemanticFunction] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    complexity: str = "low"         # "low" | "medium" | "high"
    ui_elements: UIElements | None = None
    approved: bool = False
    approved_by: str | None = None

    # Serialization: to_dict() / from_dict()
    # to_dict() must output camelCase keys and omit ui_elements if None

@dataclass
class CrossModuleData:
    dependency_graph: dict[str, dict[str, list[str]]]  # {"login": {"depends_on": ["UserService"]}}
    table_ownership: dict[str, list[str]]               # {"users": ["UserService"]}
    shared_state: dict[str, dict[str, list[str]]]       # {"session.userId": {"writtenBy": [...], "readBy": [...]}}

    # Serialization: to_dict() / from_dict()
```

### 4.3 Architecture Models (Step 5b output)

```python
@dataclass
class TargetStackMapping:
    adapter: str                    # "react", "go"
    components: list[str]           # ["LoginPage", "ProfilePage"]

@dataclass
class ServiceGroup:
    name: str                       # "users-service"
    modules: list[str]              # ["UserService", "login"]
    shared_tables: list[str]        # ["users"]
    reason: str                     # Why these modules are grouped
    target_stack: dict[str, TargetStackMapping]  # {"frontend": ..., "backend": ...}

@dataclass
class APIEndpoint:
    path: str                       # "POST /api/auth/login"
    request: dict                   # Request body schema
    response: dict                  # Response body schema
    source: str                     # "UserService.authenticate"

@dataclass
class APIContract:
    service: str                    # "users-service"
    endpoints: list[APIEndpoint]

@dataclass
class ComponentRoute:
    source: str                     # "UserService.authenticate"
    target: str                     # "UserHandler.Login"
    stack_layer: str                # "backend" | "frontend" | "workers"
    agent: str                      # "logic" | "ui" | "db" | "auth" | "form" | "task" | "email"

@dataclass
class ArchitectureDecision:
    service_groups: list[ServiceGroup]
    api_contracts: list[APIContract]
    component_routing: list[ComponentRoute]
    data_mapping: dict[str, str]    # {"session.userId": "JWT claim: sub"}

    # Serialization: to_dict() / from_dict()
```

### 4.4 Lock Models (Step 5a/5d output)

```python
@dataclass
class LockedModule:
    status: str                     # "locked"
    approved_by: str
    approved_at: str                # ISO 8601
    semantics: dict                 # Full semantic model as dict
    corrections: list[dict]         # Applied corrections
    checksum: str                   # "sha256:abc123..."

@dataclass
class SemanticLock:
    lock_version: str               # "1.0"
    locked_at: str                  # ISO 8601
    locked_by: str
    modules: dict[str, LockedModule]
    cross_module: dict | None = None

@dataclass
class ArchitectureLock:
    lock_type: str                  # "architecture"
    lock_version: str               # "1.0"
    locked_at: str                  # ISO 8601
    locked_by: str
    architecture: dict              # Full architecture decisions as dict
    checksum: str

@dataclass
class LockManifest:
    lock_type: str                  # "semantic"
    version: str
    locked_at: str
    module_count: int
    checksums: dict[str, str]       # {module_name: checksum}
    architecture_lock: dict | None = None  # Added when architecture is locked
    fully_locked: bool = False
```

### 4.5 Agent Definition Model

```python
@dataclass
class AgentDefinition:
    name: str                       # "cf-logic-agent"
    applies_to: list[str]           # ["cffunction", "cfcomponent", "cfscript"]
    system_prompt: str              # Multi-line prompt
    conventions: str                # Language conventions text
    output_schema: dict             # Expected output JSON shape
    stages: list[str]               # ["extract", "generate", "verify"]

    @classmethod
    def from_yaml(cls, path: str) -> AgentDefinition:
        """Load from a YAML file."""
        ...
```

### 4.6 Context Packet Model

```python
@dataclass
class ContextPacket:
    agent: AgentDefinition          # Which agent handles this
    task_instruction: str           # What to do (stage-specific)
    input_data: str                 # AST nodes, semantic model, or locked mapping (serialized)
    prior_results: str              # Results from earlier sub-tasks
    output_schema: dict             # Expected output shape
    token_budget: int               # Max response tokens
    metadata: dict = field(default_factory=dict)  # stage, module_name, chunk_index, etc.
```

### 4.7 Verification Models

```python
@dataclass
class EndpointVerification:
    endpoint: str                   # "POST /api/auth/login"
    source: str                     # "authenticate"
    status: str                     # "PASS" | "FAIL" | "NEEDS REVIEW"
    detail: str

@dataclass
class MappingConformance:
    rule: str                       # "User Authentication"
    status: str                     # "CONFORMS" | "DIVERGES"
    detail: str

@dataclass
class VerificationReport:
    service: str
    endpoints: list[EndpointVerification]
    mapping_conformance: list[MappingConformance]
    verdict: str                    # "PASS" | "FAIL" | "PASS (with notes)"
```

### 4.8 JSON Key Convention

**Critical**: All JSON files written to `.modernize/` use **camelCase** keys (matching the mock tool output and DESIGN-v2.md examples). Python dataclass fields use **snake_case**. The `to_dict()` methods must convert.

Example:
- Python: `business_rule`, `data_access`, `state_writes`, `control_flow`, `called_by`, `stack_layer`
- JSON: `businessRule`, `dataAccess`, `stateWrites`, `controlFlow`, `calledBy`, `stackLayer`

Implement a helper function in `core/models.py`:

```python
def to_camel_case(snake_str: str) -> str:
    parts = snake_str.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])
```

---

## 5. Phase 1: Foundation + Core Engine

### 5.1 `core/state.py` — ProjectState

Manages the `.modernize/` directory. This is nearly identical to the mock's `core/state.py` but with added validation.

```python
class ProjectState:
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.modernize_dir = self.project_path / ".modernize"
        self.migration_file = self.modernize_dir / "migration.json"

    @property
    def is_initialized(self) -> bool: ...

    def init(self, source_path: str, target_stack: list[dict], provider: str,
             trust_level: str, model: str | None = None) -> None:
        """Create .modernize/ directory structure and migration.json.
        Directory structure: ast, semantics, docs, corrections, locked,
        architecture, services, recordings, audit, components.
        migration.json schema: see mock_tool/core/state.py for exact shape."""
        ...

    def load(self) -> dict:
        """Load migration.json. Raises StateError if not initialized."""
        ...

    def save(self, state: dict) -> None:
        """Write migration.json atomically (write to .tmp then rename)."""
        ...

    def update_step(self, step: str, status: str, **extra) -> None:
        """Update a pipeline step's status. Sets currentStep on completion."""
        ...

    def get_step_status(self, step: str) -> str:
        """Return 'pending', 'completed', 'in_progress', etc."""
        ...

    def write_artifact(self, subdir: str, filename: str, data, as_json: bool = True) -> Path:
        """Write a file to .modernize/<subdir>/<filename>.
        Creates parent dirs if needed. JSON is pretty-printed with indent=2."""
        ...

    def read_artifact(self, subdir: str, filename: str, as_json: bool = True) -> dict | str | None:
        """Read an artifact. Returns None if file doesn't exist."""
        ...

    def list_artifacts(self, subdir: str, suffix: str = ".json") -> list[str]:
        """List filenames in a subdirectory matching suffix."""
        ...
```

**Atomic writes**: The `save()` and `write_artifact()` methods must write to a temp file first, then `os.replace()` it to the target path. This prevents corruption if the process is interrupted.

### 5.2 `core/sanitizer.py` — Data Redaction

The sanitizer strips sensitive data before sending to AI. In v2, it works on **AST node values** and **semantic model fields**, not raw source code.

```python
@dataclass
class RedactionRule:
    category: str       # "datasource", "credentials", "hostnames", "emails", "pii", "env"
    pattern: str        # Regex pattern
    placeholder: str    # "DATASOURCE", "CREDENTIAL", "HOST", "EMAIL", "PII", "ENV_VAR"

class Sanitizer:
    # Built-in patterns per category (see DESIGN.md for full table):
    BUILTIN_PATTERNS = {
        "datasource": [r"datasource\s*=\s*[\"']?[\w\-\.]+", r"jdbc:[^\s\"']+", r"DSN\s*=\s*\w+"],
        "credentials": [r"password\s*=\s*[\"'][^\"']+", r"apikey\s*=\s*\w+", r"token\s*=\s*\w+", r"secret\s*=\s*\w+"],
        "hostnames": [r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", r"[\w\-]+\.(internal|local|corp|private)\b", r"[\w\-]+\.[\w\-]+\.(internal|local|corp)\b"],
        "emails": [r"[\w\.\-]+@[\w\.\-]+\.\w+"],
        "pii": [r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b", r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"],
        "env": [r"process\.env\.\w+", r"\$\{[A-Z_]+\}", r"os\.environ\["],
    }

    def __init__(self, rules_path: Path | None = None):
        """Load rules from .modernize/sanitizer-rules.json if it exists."""
        ...

    def auto_discover(self, text: str) -> dict[str, list[str]]:
        """Scan text, return {category: [matches]} for categories with hits."""
        ...

    def sanitize(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace sensitive values with stable placeholders.
        Returns (sanitized_text, redaction_map).
        The redaction_map maps placeholder → original value (for audit).
        Placeholders are stable: same value always gets same placeholder.
        Format: [CATEGORY_N] e.g. [DATASOURCE_1], [EMAIL_2]."""
        ...

    def sanitize_dict(self, data: dict) -> tuple[dict, dict[str, str]]:
        """Recursively sanitize all string values in a dict.
        Returns (sanitized_dict, redaction_map)."""
        ...

    def save_rules(self, path: Path) -> None:
        """Save current rules to sanitizer-rules.json."""
        ...
```

### 5.3 `core/chunker.py` — AST-Level Chunking

Splits AST components into chunks that fit within the AI model's context window.

```python
class Chunker:
    def __init__(self, max_input_tokens: int = 8000):
        self.max_input_tokens = max_input_tokens

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate: len(text) / 4. Good enough for chunking decisions.
        The AI provider's own estimateTokens() is used for exact budgeting."""
        return len(text) // 4

    def chunk_ast(self, ast: ASTComponent) -> list[dict]:
        """Split an AST component into chunks.
        Strategy:
        1. Try the whole component as one chunk
        2. If too large, split by function (each function = one chunk)
        3. If a single function is too large, split by sub-elements
           (queries as one chunk, conditionals as another)
        Each chunk is a dict with: {"type": "full"|"function"|"sub", "data": ..., "context": ...}
        """
        ...

    def chunk_semantic(self, module: SemanticModule) -> list[dict]:
        """Same strategy but for semantic modules (used in architect + generator)."""
        ...
```

### 5.4 `core/context_assembler.py` — Build Context Packets

```python
class ContextAssembler:
    def __init__(self, sanitizer: Sanitizer, chunker: Chunker):
        self.sanitizer = sanitizer
        self.chunker = chunker

    def assemble(
        self,
        agent: AgentDefinition,
        task_instruction: str,
        input_data: str | dict,
        prior_results: str = "",
        token_budget: int = 4096,
        metadata: dict | None = None,
    ) -> ContextPacket:
        """Build a context packet:
        1. Serialize input_data to string if dict
        2. Sanitize the input_data string
        3. Combine: agent.system_prompt + agent.conventions + task_instruction + prior_results + sanitized input + output_schema
        4. Verify total fits within model's input budget (estimate tokens)
        5. If too large, raise an error (caller should use chunker first)
        """
        ...
```

### 5.5 `core/aggregator.py` — Merge Multi-Chunk Results

```python
class ResultAggregator:
    def aggregate_semantic_results(self, results: list[dict]) -> dict:
        """Merge partial semantic extraction results from multiple chunks.
        Strategy: concatenate function lists, merge dependency lists (dedupe),
        union table lists, take max complexity."""
        ...

    def aggregate_architecture_results(self, results: list[dict]) -> dict:
        """Merge partial architecture recommendations."""
        ...

    def aggregate_generation_results(self, results: list[dict]) -> list[dict]:
        """Merge generated code from multiple chunks into file list."""
        ...
```

### 5.6 `core/audit.py` — Audit Logging

```python
class AuditLogger:
    def __init__(self, audit_dir: Path):
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def log_ai_call(
        self,
        stage: str,                 # "extract", "architect", "generate", "verify"
        module: str,                # "UserService" or "users-service"
        provider: str,              # "claude", "openai", "gemini"
        model: str,                 # "claude-sonnet-4-6"
        input_tokens: int,
        output_tokens: int,
        redacted_fields: list[str], # What was sanitized
        request_summary: str,       # First 200 chars of prompt
        response_summary: str,      # First 200 chars of response
        duration_ms: int,
    ) -> Path:
        """Write audit entry to .modernize/audit/<timestamp>_<stage>_<module>.json.
        Timestamp format: YYYY-MM-DDTHH-MM-SS (filesystem-safe).
        Returns path to the audit file."""
        ...

    def list_entries(self) -> list[dict]:
        """List all audit entries, sorted by timestamp."""
        ...

    def summarize(self) -> dict:
        """Return summary: total calls, tokens used, cost estimate, per-stage breakdown."""
        ...
```

### 5.7 `providers/base.py` — AI Provider Interface

```python
from abc import ABC, abstractmethod

@dataclass
class ModelInfo:
    name: str                       # "claude-sonnet-4-6"
    max_input_tokens: int           # 200000
    max_output_tokens: int          # 8192
    provider: str                   # "claude"

@dataclass
class AIResponse:
    content: str                    # Raw response text
    input_tokens: int
    output_tokens: int
    model: str
    duration_ms: int
    raw_response: dict | None = None  # Provider-specific raw response for debugging

class AIProvider(ABC):
    @abstractmethod
    def send_prompt(self, system_prompt: str, user_prompt: str,
                    output_format: str = "json") -> AIResponse:
        """Send a prompt and get a response.
        If output_format is "json", the provider should request JSON mode
        (or equivalent) from the model.
        Raises ProviderError on failure."""
        ...

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """Return model capabilities."""
        ...

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for the given text."""
        ...
```

### 5.8 `providers/claude.py` — Claude Adapter

```python
class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-6"):
        """Initialize. api_key defaults to ANTHROPIC_API_KEY env var.
        Import anthropic lazily here (not at module level)."""
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def send_prompt(self, system_prompt: str, user_prompt: str,
                    output_format: str = "json") -> AIResponse:
        """Use client.messages.create().
        Set max_tokens from model info.
        If output_format is "json", prepend to system prompt:
        "Respond with valid JSON only. No markdown, no explanation."
        Handle anthropic.APIError → ProviderError.
        Handle anthropic.RateLimitError → ProviderError(retryable=True)."""
        ...

    def get_model_info(self) -> ModelInfo:
        """Return hardcoded model info based on self.model.
        claude-sonnet-4-6: max_input=200000, max_output=16384
        claude-haiku-4-5-20251001: max_input=200000, max_output=8192
        claude-opus-4-6: max_input=200000, max_output=16384"""
        ...

    def estimate_tokens(self, text: str) -> int:
        """Use client.count_tokens() if available, else len(text) // 4."""
        ...
```

### 5.9 `providers/openai_provider.py` — OpenAI Adapter

```python
class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        """Import openai lazily. api_key defaults to OPENAI_API_KEY env var."""
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def send_prompt(self, system_prompt: str, user_prompt: str,
                    output_format: str = "json") -> AIResponse:
        """Use client.chat.completions.create().
        If output_format is "json", set response_format={"type": "json_object"}.
        Handle openai.APIError → ProviderError."""
        ...

    def get_model_info(self) -> ModelInfo: ...
    def estimate_tokens(self, text: str) -> int: ...
```

### 5.10 `providers/gemini.py` — Gemini Adapter

```python
class GeminiProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        """Import google.genai lazily. api_key defaults to GOOGLE_API_KEY env var."""
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def send_prompt(self, system_prompt: str, user_prompt: str,
                    output_format: str = "json") -> AIResponse:
        """Use client.models.generate_content().
        If output_format is "json", set generation_config with response_mime_type="application/json".
        Handle google.genai exceptions → ProviderError."""
        ...

    def get_model_info(self) -> ModelInfo: ...
    def estimate_tokens(self, text: str) -> int: ...
```

### 5.11 Provider Factory

In `providers/__init__.py`:

```python
def create_provider(name: str, api_key: str | None = None, model: str | None = None) -> AIProvider:
    """Factory function.
    name: "claude" | "openai" | "gemini"
    Raises ModernizeError if unknown provider.
    Uses default model per provider if model not specified:
      claude → "claude-sonnet-4-6"
      openai → "gpt-4o"
      gemini → "gemini-2.5-flash"
    """
    if name == "claude":
        from providers.claude import ClaudeProvider
        return ClaudeProvider(api_key=api_key, model=model or "claude-sonnet-4-6")
    elif name == "openai":
        from providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model or "gpt-4o")
    elif name == "gemini":
        from providers.gemini import GeminiProvider
        return GeminiProvider(api_key=api_key, model=model or "gemini-2.5-flash")
    else:
        raise ModernizeError(f"Unknown provider: {name}. Supported: claude, openai, gemini")
```

### 5.12 `agents/loader.py` — Load Agent YAML

```python
import yaml

def load_agent(yaml_path: str) -> AgentDefinition:
    """Load a single agent YAML file into an AgentDefinition.
    File format:
    ```yaml
    name: cf-logic-agent
    appliesTo: ["cffunction", "cfcomponent"]
    systemPrompt: |
      You are an expert in ColdFusion business logic...
    conventions: |
      - CFCs use <cffunction>...
    outputSchema:
      rules:
        - name: string
          description: string
          ...
    stages: [extract, generate, verify]
    ```
    """
    ...

def load_all_agents(agents_dir: str) -> list[AgentDefinition]:
    """Load all .yaml files from a directory."""
    ...
```

### 5.13 `agents/resolver.py` — Match AST Nodes to Agents

```python
class AgentResolver:
    def __init__(self, agents: list[AgentDefinition]):
        self.agents = agents

    def resolve(self, ast_node: ASTComponent | ASTFunction, stage: str) -> list[AgentDefinition]:
        """Find all agents that apply to this AST node for the given stage.
        Matching logic:
        1. Filter agents where `stage` is in agent.stages
        2. For each agent, check if any of node's characteristics match agent.applies_to
           - ASTComponent type="component" → matches "cfcomponent"
           - ASTComponent type="template" → matches "cfm"
           - ASTFunction with queries → matches "cfquery"
           - ASTFunction with scope_writes containing "session" → matches "session", "cflogin"
           - ASTFunction with function_calls to known form handlers → matches "cfform"
        3. Return matching agents sorted by specificity (most specific first)
        """
        ...

    def resolve_for_function(self, func: ASTFunction, stage: str) -> AgentDefinition:
        """Resolve the best single agent for a function. Used by the generator.
        Returns the most specific match. Falls back to the logic agent."""
        ...
```

### 5.14 `agents/registry.py` — Global Agent Registry

```python
class AgentRegistry:
    """Singleton-like registry loaded once during init."""

    def __init__(self):
        self._agents: dict[str, AgentDefinition] = {}

    def load_from_adapter(self, adapter_agents_dir: str) -> None:
        """Load all agents from an adapter's agents/ directory."""
        ...

    def get(self, name: str) -> AgentDefinition | None:
        """Get agent by name."""
        ...

    def get_for_stage(self, stage: str) -> list[AgentDefinition]:
        """Get all agents that operate in the given stage."""
        ...

    def all(self) -> list[AgentDefinition]:
        ...
```

### 5.15 `modernize.py` — CLI Entry Point

Use Click. Follow the exact same command structure as the mock (`mock_tool/modernize.py`) but with these additions:

```python
@click.group()
@click.option("--project-dir", default=".", help="Project directory (default: current)")
@click.pass_context
def cli(ctx, project_dir):
    """modernize — AI-Powered Legacy App Modernization Framework (v2)"""
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = project_dir

@cli.command()
@click.argument("source_path")
@click.option("--target-stack", required=True)
@click.option("--provider", default="claude")
@click.option("--model", default=None, help="AI model (default: provider's default)")
@click.option("--trust-level", default="standard", type=click.Choice(["strict", "standard", "trust"]))
@click.option("--execution-mode", default="guided", type=click.Choice(["guided", "supervised", "auto"]))
@click.option("--redact", default=None, help="Override auto-discovery: comma-separated categories")
@click.pass_context
def init(ctx, source_path, target_stack, provider, model, trust_level, execution_mode, redact):
    """Initialize modernization project."""
    ...
```

**All commands from the mock PLUS these additions:**

| Command | Description | Phase |
|---------|-------------|-------|
| `modernize init` | Initialize project | 1 |
| `modernize parse` | Step 1 — Parse to AST | 2 |
| `modernize extract` | Step 2 — Extract semantics | 2 |
| `modernize document` | Step 3 — Generate docs | 2 |
| `modernize review semantics [module]` | Step 4 — Review | 2 |
| `modernize correct <target> --field --value` | Apply correction | 2 |
| `modernize approve semantics <module> [--all]` | Approve | 2 |
| `modernize lock semantics` | Step 5a — Lock | 3 |
| `modernize architect` | Step 5b — Design | 3 |
| `modernize review architect` | Review architecture | 3 |
| `modernize approve architect` | Approve architecture | 3 |
| `modernize lock architecture` | Step 5d — Lock | 3 |
| `modernize generate <service>` | Step 6 — Generate code | 4 |
| `modernize review generate <service>` | Review generated code | 4 |
| `modernize verify <service>` | Step 7 — Verify | 5 |
| `modernize components register <path>` | Register client components | 4 |
| `modernize status` | Show pipeline progress | 1 |
| `modernize audit` | Show AI call audit trail | 1 |
| `modernize annotate <module> --note` | Add human knowledge | 6 |
| `modernize redact review` | Review sanitizer findings | 1 |
| `modernize redact add <category>` | Add redaction category | 1 |
| `modernize redact remove <category>` | Remove redaction category | 1 |
| `modernize redact add-pattern <pattern>` | Add custom pattern | 1 |
| `modernize run --all` | Auto mode — full pipeline | 6 |
| `modernize summary` | Post-run summary | 6 |
| `modernize unlock semantics` | Unlock for re-editing | 3 |

---

## 6. Phase 2: Parser + Extractor + ColdFusion Adapter

### 6.1 `adapters/source/base.py` — Source Adapter Interface

```python
class SourceAdapter(ABC):
    @abstractmethod
    def detect(self, files: list[str]) -> bool:
        """Does this adapter handle any of these files?
        Check file extensions: .cfc, .cfm for ColdFusion."""
        ...

    @abstractmethod
    def parse_to_ast(self, file_path: str) -> ASTComponent:
        """Parse a single source file into a semantic AST.
        This is the core method. It must:
        1. Read the file
        2. Parse syntax (tree-sitter or regex)
        3. Walk the syntax tree to extract semantic AST nodes
        4. Parse embedded SQL strings (via sql_extractor)
        5. Return a fully populated ASTComponent"""
        ...

    @abstractmethod
    def classify_ast_node(self, node: ASTFunction) -> str:
        """Classify an AST function for agent routing.
        Returns agent type: "logic", "query", "ui", "auth", "form", "task", "email".
        Classification rules for ColdFusion:
        - Has queries and no other significant logic → "query"
        - Has session scope writes → "auth"
        - Is a CFM template with form elements → "form"
        - Is a CFM template → "ui"
        - Has cfmail tags → "email"
        - Has cfschedule tags → "task"
        - Default → "logic"
        """
        ...

    @abstractmethod
    def get_agent_definitions_dir(self) -> str:
        """Return path to this adapter's agents/ directory."""
        ...

    @abstractmethod
    def get_conventions(self) -> str:
        """Return general language conventions text."""
        ...

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Return list of file extensions this adapter handles."""
        ...
```

### 6.2 `adapters/source/coldfusion/parser.py` — ColdFusion Parser

This is the most complex file in the codebase. It must parse ColdFusion's tag-based syntax into the semantic AST.

**Strategy**: Use regex-based parsing (not tree-sitter) since ColdFusion's tag syntax is XML-like and regular enough. If a tree-sitter grammar for CFML becomes available, this can be swapped out without changing the adapter interface.

```python
class ColdFusionParser:
    """Parse ColdFusion .cfc and .cfm files into semantic AST."""

    # === Regex patterns ===
    # IMPORTANT: All regexes use re.DOTALL and re.IGNORECASE

    # Component declaration
    RE_COMPONENT = re.compile(
        r'<cfcomponent\b([^>]*)>(.*?)</cfcomponent>',
        re.DOTALL | re.IGNORECASE
    )

    # Function declaration (captures everything between open and close tags)
    RE_FUNCTION = re.compile(
        r'<cffunction\b([^>]*)>(.*?)</cffunction>',
        re.DOTALL | re.IGNORECASE
    )

    # Argument declaration
    RE_ARGUMENT = re.compile(
        r'<cfargument\b([^>]*)>',
        re.IGNORECASE
    )

    # Query block
    RE_QUERY = re.compile(
        r'<cfquery\b([^>]*)>(.*?)</cfquery>',
        re.DOTALL | re.IGNORECASE
    )

    # Query parameter
    RE_QUERYPARAM = re.compile(
        r'<cfqueryparam\b([^>]*)>',
        re.IGNORECASE
    )

    # Variable set
    RE_SET = re.compile(
        r'<cfset\b\s+(.*?)>',
        re.IGNORECASE
    )

    # Conditional
    RE_IF = re.compile(
        r'<cfif\b\s+(.*?)>(.*?)</cfif>',
        re.DOTALL | re.IGNORECASE
    )

    # Exception throw
    RE_THROW = re.compile(
        r'<cfthrow\b([^>]*)>',
        re.IGNORECASE
    )

    # Return
    RE_RETURN = re.compile(
        r'<cfreturn\b\s+(.*?)>',
        re.IGNORECASE
    )

    # Transaction block
    RE_TRANSACTION = re.compile(
        r'<cftransaction\b[^>]*>(.*?)</cftransaction>',
        re.DOTALL | re.IGNORECASE
    )

    # Property set (variables-scope)
    RE_PROPERTY = re.compile(
        r'<cfset\s+variables\.(\w+)\s*=\s*(.*?)>',
        re.IGNORECASE
    )

    # Location (redirect)
    RE_LOCATION = re.compile(
        r'<cflocation\b([^>]*)>',
        re.IGNORECASE
    )

    # Try/Catch
    RE_TRY = re.compile(
        r'<cftry>(.*?)</cftry>',
        re.DOTALL | re.IGNORECASE
    )
    RE_CATCH = re.compile(
        r'<cfcatch\b([^>]*)>(.*?)</cfcatch>',
        re.DOTALL | re.IGNORECASE
    )

    # Function call detection (CFScript style and tag style)
    RE_FUNCTION_CALL = re.compile(
        r'(\w+(?:\.\w+)*)\s*\(([^)]*)\)',
        re.IGNORECASE
    )

    # createObject call
    RE_CREATE_OBJECT = re.compile(
        r'createObject\s*\(\s*["\']component["\']\s*,\s*["\'](\w+)["\']\s*\)',
        re.IGNORECASE
    )

    def parse_file(self, file_path: str) -> ASTComponent:
        """Main entry point. Determine file type and parse accordingly.
        .cfc files → parse as component
        .cfm files → parse as template"""
        content = Path(file_path).read_text(encoding="utf-8")
        filename = Path(file_path).name

        if filename.endswith(".cfc"):
            return self._parse_component(content, filename)
        else:
            return self._parse_template(content, filename)

    def _parse_component(self, content: str, filename: str) -> ASTComponent:
        """Parse a CFC component file.
        1. Extract component tag attributes (name, extends, displayname)
        2. Extract properties (<cfset variables.xxx = ...>)
        3. Extract all functions
        4. For each function, parse: arguments, queries, sets, conditionals, throws, returns, function calls
        5. Detect transaction blocks and mark functions as transactional
        """
        ...

    def _parse_template(self, content: str, filename: str) -> ASTComponent:
        """Parse a CFM template file.
        1. Name = filename without extension
        2. Type = "template"
        3. Treat the entire file body as a single function named "(page_logic)"
        4. Extract conditionals, function calls, queries, etc. from the template body
        5. Detect form elements (cfform, cfinput) and component instantiation (createObject)
        """
        ...

    def _parse_function(self, attrs: str, body: str) -> ASTFunction:
        """Parse a single cffunction.
        1. Extract attributes: name, access, returntype from the tag attributes string
        2. Parse arguments from body
        3. Parse queries from body (delegate SQL to sql_extractor)
        4. Parse cfset statements → scope writes (session.X, application.X)
        5. Parse cfif blocks → conditionals
        6. Parse cfthrow → conditional actions
        7. Parse cfreturn → return type info
        8. Detect if wrapped in cftransaction
        9. Parse function calls (both tag-style invocations and script-style)
        """
        ...

    def _extract_tag_attributes(self, attrs_str: str) -> dict[str, str]:
        """Parse tag attributes string into dict.
        Handles: name="value", name='value', name=value (no quotes).
        Example: 'name="authenticate" access="public" returntype="struct"'
        → {"name": "authenticate", "access": "public", "returntype": "struct"}
        """
        ...

    def _parse_scope_writes(self, body: str) -> list[ASTScopeWrite]:
        """Extract session.X = Y, application.X = Y, request.X = Y assignments.
        Parse: <cfset session.userId = qUser.id>
        → ASTScopeWrite(scope="session", key="userId", value="qUser.id")
        """
        ...

    def _parse_conditionals(self, body: str) -> list[ASTConditional]:
        """Extract cfif blocks and determine their actions.
        Look at the cfif body for: cfthrow, cfreturn, cfset, cflocation.
        Example:
          <cfif qUser.recordCount EQ 0>
            <cfthrow type="InvalidCredentials" message="User not found">
          </cfif>
        → ASTConditional(
            condition="qUser.recordCount EQ 0",
            action="throw",
            detail="InvalidCredentials: User not found"
          )
        """
        ...

    def _parse_function_calls(self, body: str) -> list[ASTFunctionCall]:
        """Extract function calls from body.
        Handles:
        - Direct calls: hashVerify(arguments.password, qUser.password_hash)
        - Object calls: userService.authenticate(form.email, form.password)
        - createObject: createObject("component", "UserService")
        Skip built-in CF functions like: now(), structKeyExists(), isDefined(), etc.
        BUILTIN_FUNCTIONS = {"now", "structkeyexists", "isdefined", "dateadd", "len",
                             "trim", "lcase", "ucase", "val", "int", "isnumeric", ...}
        """
        ...
```

**Validation**: After parsing, the parser must verify that the output matches the expected structure. Write a test for each sample CF file in `mock_tool/sample_app/` that verifies the parser produces the exact same AST structure as the mock data in `mock_tool/mock_data/ast_data.py`. The expected outputs are the ground truth.

### 6.3 `adapters/source/coldfusion/sql_extractor.py` — SQL Parsing

```python
import sqlglot

class SQLExtractor:
    """Extract structured information from SQL strings found in cfquery tags."""

    def extract(self, sql: str) -> dict:
        """Parse a SQL string and return:
        {
            "operation": "SELECT" | "INSERT" | "UPDATE" | "DELETE",
            "tables": ["users", "orders"],
            "columns": ["id", "email", ...],  # For SELECT only
            "filter": "email = ?",             # WHERE clause simplified
        }
        Uses sqlglot for parsing.
        If sqlglot fails (e.g., CF variable interpolation in SQL), fall back to regex:
        - operation: first word
        - tables: FROM/INTO/UPDATE followed by table name
        - columns: between SELECT and FROM
        """
        ...

    def normalize_cf_sql(self, raw_sql: str) -> str:
        """Pre-process ColdFusion SQL to make it parseable by sqlglot:
        - Replace <cfqueryparam ...> tags with ? placeholders
        - Replace #variable# interpolations with ? placeholders
        - Strip CF comments
        - Normalize whitespace
        """
        ...
```

### 6.4 `adapters/source/coldfusion/adapter.py` — ColdFusion Adapter

```python
class ColdFusionAdapter(SourceAdapter):
    def __init__(self):
        self.parser = ColdFusionParser()
        self.sql_extractor = SQLExtractor()

    def detect(self, files: list[str]) -> bool:
        return any(f.endswith((".cfc", ".cfm")) for f in files)

    def parse_to_ast(self, file_path: str) -> ASTComponent:
        return self.parser.parse_file(file_path)

    def classify_ast_node(self, node: ASTFunction) -> str:
        """Classification priority (highest to lowest):
        1. Has cfmail/cfschedule references → "email" / "task"
        2. Has session scope writes → "auth"
        3. Has queries and minimal other logic → "query"
        4. Is from a template file → "ui"
        5. Default → "logic"
        """
        ...

    def get_agent_definitions_dir(self) -> str:
        return str(Path(__file__).parent / "agents")

    def get_conventions(self) -> str:
        return """ColdFusion conventions:
- CFCs (*.cfc) are components with methods declared via <cffunction>
- CFM (*.cfm) are templates that mix HTML and CF tags
- Scope hierarchy: variables (private), this (public), arguments (params)
- Session scope: server-side user state (session.userId, session.userRole)
- Application scope: app-wide shared state
- <cfquery> executes SQL, <cfqueryparam> provides parameterized values
- <cftransaction> wraps multiple queries in a DB transaction
- hashVerify() compares a plaintext password against a bcrypt hash
- createObject("component", "Name") instantiates a CFC
- <cfthrow type="..." message="..."> raises typed exceptions
- <cfcatch type="..."> catches specific exception types
"""

    def get_supported_extensions(self) -> list[str]:
        return [".cfc", ".cfm"]
```

### 6.5 Agent YAML Definitions

Create these 7 YAML files in `app/adapters/source/coldfusion/agents/`. Each follows the schema defined in DESIGN.md (agent system section).

**`cf-logic-agent.yaml`**:
```yaml
name: cf-logic-agent
appliesTo: ["cffunction", "cfcomponent", "cfscript"]
systemPrompt: |
  You are an expert in ColdFusion business logic and component architecture.
  You understand CFC components, cffunction declarations, the variables/this/session/application
  scope hierarchy, argument handling, error throwing via cfthrow, and ColdFusion's
  implicit type coercion. You analyze AST nodes (not raw source code) to extract
  business rules that the code implements.

  When identifying business rules:
  - Name the rule in business terms, not code terms ("User Authentication" not "authenticate function")
  - Describe what the function accomplishes for the business, including edge cases
  - Note any implicit rules hidden in conditionals or calculations
  - Flag any state mutations (session writes, application scope changes)
  - Note transactional boundaries

conventions: |
  - CFCs use <cffunction> with access=public/private/remote/package
  - variables scope = instance state (private to the component)
  - this scope = public properties (accessible outside the component)
  - arguments scope = function parameters
  - session scope = per-user server-side state
  - application scope = app-wide shared state
  - init() is the constructor pattern
  - extends= declares inheritance from a parent component
  - returntype= declares the function return type (struct, query, void, string, numeric, boolean, any)

outputSchema:
  businessRule:
    name: string
    description: string
    confidence: number

stages: [extract, generate, verify]
```

**Create similar YAML files for**: `cf-query-agent.yaml`, `cf-ui-agent.yaml`, `cf-auth-agent.yaml`, `cf-form-agent.yaml`, `cf-task-agent.yaml`, `cf-email-agent.yaml`.

Each agent's `systemPrompt` and `conventions` must reflect the specific domain knowledge described in DESIGN.md's agent table (DB Agent knows SQL dialects, UI Agent knows template→JSX, Auth Agent knows session→JWT, etc.).

The `appliesTo` fields:
- cf-query-agent: `["cfquery", "cfstoredproc", "cfprocparam", "queryExecute"]`
- cf-ui-agent: `["cfm", "cfform", "cfoutput", "cfinput"]`
- cf-auth-agent: `["session", "cflogin", "cflogout"]`
- cf-form-agent: `["cfform", "cfinput", "cfselect"]`
- cf-task-agent: `["cfschedule", "cfthread"]`
- cf-email-agent: `["cfmail", "cfmailpart"]`

### 6.6 `pipeline/parser.py` — Step 1: Parse to AST

```python
def run_parse(state: ProjectState) -> None:
    """Step 1 — Parse legacy source to AST.

    Flow:
    1. Verify project is initialized
    2. Load migration.json to get source path
    3. Detect source language by scanning files
    4. Instantiate the correct source adapter
    5. Find all source files (walk the source directory)
    6. For each file:
       a. Call adapter.parse_to_ast(file_path) → ASTComponent
       b. Call ast.to_dict() → JSON-serializable dict
       c. Write to .modernize/ast/<filename>.ast.json
    7. Display progress (Rich progress bar) and AST tree visualization (Rich Tree)
    8. Update pipeline step to "completed"

    Error handling:
    - If a file fails to parse, log the error, skip the file, and continue
    - Report skipped files at the end
    - Only mark step as "completed" if at least one file was parsed successfully
    """
    ...
```

**Rich output**: Copy the exact UX from `mock_tool/pipeline/parser.py` — spinner during parsing, then a Rich Tree showing the AST structure for each file. The tree visualization function `_build_ast_tree()` from the mock is good; replicate it.

### 6.7 `pipeline/extractor.py` — Step 2: Extract Semantics

```python
def run_extract(state: ProjectState) -> None:
    """Step 2 — Extract semantics from AST.

    Flow:
    1. Verify "parse" step is completed
    2. Load all AST artifacts from .modernize/ast/
    3. Load the AI provider (from migration.json config)
    4. Load agent definitions via the source adapter
    5. For each AST component:
       a. Deterministic extraction (NO AI):
          - Function signatures → SemanticFunction.signature
          - Query nodes → SemanticFunction.data_access
          - Scope writes → SemanticFunction.state_writes
          - Conditionals → SemanticFunction.control_flow
          - Function calls → SemanticFunction.calls
          - Cross-reference calledBy (reverse the call graph)
       b. AI-assisted extraction (MINIMAL):
          - For each function, send AST nodes to the appropriate agent
          - Task: "What business rule does this function implement? Name it in business terms."
          - Parse AI response → BusinessRule(name, description, confidence)
          - Tag with source="ai"
       c. Classify complexity: low (<3 functions, no transactions),
          medium (3-5 functions or transactions),
          high (>5 functions or complex transactions)
    6. Build cross-module data:
       - dependency_graph: from function calls that reference other modules
       - table_ownership: from data_access across all modules
       - shared_state: from scope writes/reads across all modules
    7. Write .modernize/semantics/<module>.semantic.json for each module
    8. Write .modernize/semantics/cross-module.json
    9. Update pipeline step

    AI usage:
    - Create context packet per function using ContextAssembler
    - Send via AIProvider.send_prompt()
    - Log every AI call via AuditLogger
    - Parse JSON response, validate against expected schema
    - If AI call fails, fall back to a generic business rule:
      BusinessRule(name=function_name, description="[AI extraction failed]", source="deterministic", confidence=50)
    """
    ...
```

**Deterministic extraction detail**: The deterministic part is a straightforward translation from AST nodes to semantic model fields. Here's the mapping:

| AST Node | Semantic Field | Transformation |
|----------|---------------|----------------|
| `ASTFunction.arguments` | `SemanticFunction.signature.inputs` | Direct copy: `[{"name": arg.name, "type": arg.type, "required": arg.required}]` |
| `ASTFunction.returns` | `SemanticFunction.signature.outputs` | Direct copy |
| `ASTFunction.queries` | `SemanticFunction.data_access` | Map each query: `DataAccess(table=q.tables[0], operation=q.operation, columns=extracted_from_sql, parameterized=q.parameterized)` |
| `ASTFunction.scope_writes` | `SemanticFunction.state_writes` | Map each: `StateWrite(scope=sw.scope, key=sw.key)` |
| `ASTFunction.conditionals` | `SemanticFunction.control_flow` | Map each: `ControlFlowRule(condition=c.condition, action=c.action)` |
| `ASTFunction.function_calls` | `SemanticFunction.calls` | Extract target names: `[fc.target for fc in func.function_calls]` |
| `ASTFunction.transactional` | `SemanticFunction.transactional` | Direct copy |

### 6.8 `pipeline/documenter.py` — Step 3: Generate Review Docs

```python
def run_document(state: ProjectState) -> None:
    """Step 3 — Generate review documentation from semantic model.

    Flow:
    1. Verify "extract" step is completed
    2. Load all semantic artifacts from .modernize/semantics/
    3. For each module:
       a. Generate markdown doc from semantic model (template-driven, mostly NO AI)
       b. Optionally use AI for prose summaries (if available)
       c. Write to .modernize/docs/<module>.md
    4. Generate overview doc (.modernize/docs/overview.md)
    5. Update pipeline step

    Document template: Follow the exact template from DESIGN-v2.md Step 3 section.
    Copy the markdown generation logic from mock_tool/pipeline/documenter.py —
    that implementation (_generate_module_doc, _generate_overview) is correct
    and production-ready. The only change: read from semantic JSON files
    instead of mock_data.
    """
    ...
```

### 6.9 `pipeline/reviewer.py` — Step 4: Interactive Review

```python
def run_review(state: ProjectState, module_name: str | None = None) -> None:
    """Interactive review. Copy behavior from mock_tool/pipeline/reviewer.py exactly.
    If module_name is None, show status table for all modules.
    If module_name is given, walk through AI-extracted items interactively."""
    ...

def run_correct(state: ProjectState, target: str, field: str, value: str) -> None:
    """Apply a correction. Format: ModuleName.functionName --field X --value Y.
    Write to .modernize/corrections/<module>.corrections.json.
    Also update the semantic model in .modernize/semantics/<module>.semantic.json."""
    ...

def run_approve(state: ProjectState, module_name: str | None, approve_all: bool) -> None:
    """Approve module semantics. When all modules approved, mark review step completed."""
    ...
```

**Important behavioral detail**: `run_correct()` must update BOTH the corrections file AND the semantic model file. The mock only writes to corrections; the production tool must also apply the correction to the semantic JSON so that downstream steps see the corrected values.

---

## 7. Phase 3: Lock Manager + Architect Module

### 7.1 `pipeline/locker.py` — Lock Manager

```python
def run_lock_semantics(state: ProjectState) -> None:
    """Step 5a — Lock semantic mappings.

    Flow:
    1. Verify all modules are approved (review step completed)
    2. Load all semantic models from .modernize/semantics/
    3. Apply any pending corrections from .modernize/corrections/
    4. For each module:
       a. Serialize the corrected semantic model to JSON (sorted keys)
       b. Compute SHA-256 checksum
       c. Build LockedModule object
    5. Load cross-module data
    6. Build SemanticLock and LockManifest
    7. Write .modernize/locked/semantic-lock.json
    8. Write .modernize/locked/lock-manifest.json
    9. Update pipeline step

    Copy logic from mock_tool/pipeline/locker.py but add:
    - Actually apply corrections to the semantic model (mock has a pass statement)
    - Validate checksums are unique per module (sanity check)
    """
    ...

def run_lock_architecture(state: ProjectState) -> None:
    """Step 5d — Lock architecture decisions.
    Copy logic from mock_tool/pipeline/locker.py.
    Add architecture checksum to lock-manifest.json.
    Set fullyLocked=True.
    Update serviceGroups in migration.json."""
    ...

def verify_lock_integrity(state: ProjectState) -> bool:
    """Verify that locked files haven't been tampered with.
    Re-compute checksums and compare against lock-manifest.json.
    Returns True if all checksums match."""
    ...

def run_unlock_semantics(state: ProjectState) -> None:
    """Unlock semantic mappings for re-editing.
    1. Verify semantics are currently locked
    2. Remove .modernize/locked/semantic-lock.json
    3. Update lock-manifest.json (remove semantic checksums, set fullyLocked=False)
    4. Reset review step to "pending" for all modules
    5. Reset lock_semantics step to "pending"
    If architecture is also locked, require explicit --force flag
    (because unlocking semantics invalidates the architecture too)."""
    ...
```

### 7.2 `pipeline/architect.py` — Step 5b: Design Architecture

```python
def run_architect(state: ProjectState) -> None:
    """Step 5b — Design target architecture from locked semantics.

    Flow:
    1. Verify semantics are locked
    2. Load semantic lock from .modernize/locked/semantic-lock.json
    3. Load AI provider
    4. AI tasks (each is a separate AI call):
       a. group_service_boundaries: Analyze dependency graph + shared tables → suggest service groups
       b. define_api_contracts: For each service group, define REST endpoints
       c. route_components: Map legacy functions → target components + stack layers
       d. map_data: Map legacy state (session/application) to modern equivalents (JWT/env vars)
    5. Build ArchitectureDecision from AI results
    6. Generate artifacts:
       a. .modernize/architecture/architecture-decisions.json (machine-readable)
       b. .modernize/architecture/architecture-blueprint.md (index — see mock for format)
       c. .modernize/architecture/services/<service-name>.md (per-service docs)
       d. .modernize/architecture/cross-cutting.md (state mapping, risks, infra)
    7. Update pipeline step

    AI prompts:
    For service grouping:
      System: "You are a software architect designing microservice boundaries."
      User: "Given these modules with their dependencies and shared tables,
             group them into 3-7 service boundaries. Explain your rationale."
      Input: serialized locked semantic model (all modules)
      Output: JSON with serviceGroups array

    For API contracts:
      System: "You are designing REST API contracts for a modern Go + React application."
      User: "Given this service group and its functions, define REST endpoints."
      Input: service group modules + their semantic functions
      Output: JSON with endpoints array

    For component routing:
      System: "You are routing legacy components to modern stack layers."
      User: "Map each legacy function to its target component, stack layer, and agent type."
      Input: all functions + target stack configuration
      Output: JSON with componentRouting array

    For data mapping:
      System: "You are migrating from ColdFusion server-side state to modern stateless architecture."
      User: "Map each legacy state reference to its modern equivalent."
      Input: shared_state from cross-module data + target stack
      Output: JSON with dataMapping dict

    Architecture blueprint markdown:
    Copy the exact formats from mock_tool/mock_data/architecture_data.py
    (get_blueprint_index_md, get_service_blueprint_md, get_cross_cutting_md).
    These are templates — populate them from the AI-generated architecture decisions.
    """
    ...

def run_review_architect(state: ProjectState) -> None:
    """Show architecture review status. Copy from mock."""
    ...

def run_approve_architect(state: ProjectState) -> None:
    """Approve architecture. Copy from mock."""
    ...
```

---

## 8. Phase 4: Generator Module + React/Go Adapters

### 8.1 `adapters/target/base.py` — Target Adapter Interface

```python
class TargetAdapter(ABC):
    @abstractmethod
    def role(self) -> str:
        """Stack layer: "frontend", "backend", "workers"."""
        ...

    @abstractmethod
    def scaffold(self, service_name: str, output_dir: Path) -> None:
        """Create project skeleton (package.json, go.mod, folder structure)."""
        ...

    @abstractmethod
    def get_conventions(self) -> str:
        """Return target language conventions for AI context."""
        ...

    @abstractmethod
    def get_prompts(self, stage: str) -> dict[str, str]:
        """Return AI prompts specific to this target for a given stage.
        Keys: agent types ("logic", "ui", "db", "auth", etc.)
        Values: prompt strings."""
        ...
```

### 8.2 `adapters/target/react/adapter.py`

```python
class ReactAdapter(TargetAdapter):
    def role(self) -> str:
        return "frontend"

    def scaffold(self, service_name: str, output_dir: Path) -> None:
        """Create React project skeleton:
        <output_dir>/
        ├── package.json
        ├── tsconfig.json
        ├── vite.config.ts
        ├── src/
        │   ├── main.tsx
        │   ├── App.tsx
        │   ├── api/           # API client (generated from contracts)
        │   ├── pages/         # Page components
        │   ├── components/    # Shared components
        │   └── hooks/         # Custom hooks
        └── public/
        """
        ...

    def get_conventions(self) -> str:
        return """React + TypeScript conventions:
- Functional components only (no class components)
- React Router for navigation (useNavigate, useParams)
- Custom hooks for shared logic (useAuth, useApi)
- TypeScript strict mode
- Forms: controlled components with useState
- Error display: conditional rendering of error banners
- API calls: async/await with try/catch
- Loading states: useState<boolean> for isLoading
- No CSS-in-JS — use plain CSS or CSS modules
"""

    def get_prompts(self, stage: str) -> dict[str, str]:
        if stage == "generate":
            return {
                "ui": """Generate a React TypeScript component from the locked mapping.
Requirements:
- Functional component with proper TypeScript types
- Use React Router hooks (useNavigate, useParams) for navigation
- Use the provided API client for backend calls
- Handle loading states and errors
- Preserve all business rules from the mapping
- Include accessibility attributes (role, aria-label) where appropriate""",
                "form": """Generate a React form component from the locked mapping.
Requirements:
- Controlled form with useState for each field
- Client-side validation matching the business rules
- Submit handler with loading state and error handling
- Display validation errors inline
- Preserve all form fields and links from the mapping""",
            }
        return {}
```

### 8.3 `adapters/target/go/adapter.py`

```python
class GoAdapter(TargetAdapter):
    def role(self) -> str:
        return "backend"

    def scaffold(self, service_name: str, output_dir: Path) -> None:
        """Create Go project skeleton:
        <output_dir>/
        ├── go.mod
        ├── go.sum
        ├── cmd/
        │   └── server/
        │       └── main.go         # Entry point with Chi router
        ├── internal/
        │   ├── auth/
        │   │   ├── jwt.go          # JWT service
        │   │   └── middleware.go   # Auth middleware
        │   ├── handlers/           # HTTP handlers
        │   ├── store/              # Database access layer
        │   └── models/             # Go structs
        └── migrations/             # SQL migration files
        """
        ...

    def get_conventions(self) -> str:
        return """Go + Chi conventions:
- Handler signature: func (h *Handler) Method(w http.ResponseWriter, r *http.Request)
- Chi router for HTTP routing
- JSON request/response: encoding/json
- Error responses: http.Error(w, message, statusCode)
- Database: database/sql with pgx driver
- Transactions: db.BeginTx() with defer tx.Rollback() and tx.Commit()
- JWT: golang.org/x/crypto for bcrypt, custom JWT package
- Context: r.Context() for request-scoped data
- Error handling: explicit error returns, no panic
- Structured logging with slog
"""

    def get_prompts(self, stage: str) -> dict[str, str]:
        if stage == "generate":
            return {
                "logic": """Generate a Go HTTP handler from the locked semantic mapping.
Requirements:
- Follow Chi router handler conventions
- Parse JSON request body with proper error handling
- Implement ALL business rules from the mapping exactly
- Use the store layer for database access (don't write raw SQL in handlers)
- Return JSON responses
- Use proper HTTP status codes
- Add comments referencing the source mapping (e.g., "Source: UserService.authenticate")""",
                "db": """Generate Go database store functions from the locked mapping.
Requirements:
- Use database/sql with prepared statements
- Parameterize all queries (prevent SQL injection)
- Use transactions where the mapping indicates transactional=true
- Return Go structs, not raw sql.Rows
- Handle sql.ErrNoRows appropriately""",
                "auth": """Generate Go JWT authentication middleware and service from the locked mapping.
Requirements:
- Map ColdFusion session state to JWT claims
- Generate token on login, validate on protected routes
- Use bcrypt for password hashing (maps from CF hashVerify)
- Middleware extracts user info from JWT into request context""",
            }
        return {}
```

### 8.4 `pipeline/generator.py` — Step 6: Generate Code

```python
def run_generate(state: ProjectState, service_name: str) -> None:
    """Step 6 — Generate code for a service group from locked mappings.

    Flow:
    1. Verify both semantic and architecture locks exist (fullyLocked=True)
    2. Verify lock integrity (checksums match)
    3. Load architecture lock → find the service group
    4. Load semantic lock → get modules for this service group
    5. Load target adapters (from migration.json target stack config)
    6. Load AI provider
    7. Load agent definitions

    For each component in the service group's componentRouting:
      a. Determine target adapter based on stackLayer (frontend/backend)
      b. Determine agent based on routing's agent field
      c. Build the AI prompt:
         - System: agent.system_prompt + target_adapter.conventions
         - User: target_adapter.get_prompts(stage="generate")[agent_type]
                + "LOCKED SEMANTIC MAPPING:\n" + serialized locked mapping for this function
                + "API CONTRACT:\n" + relevant endpoint from architecture lock
                + "TARGET CONVENTIONS:\n" + target_adapter.get_conventions()
                + client components context (if registered)
      d. Send to AI provider
      e. Parse response as generated code
      f. Write to .modernize/services/<service>/<layer>/<filename>

    8. Scaffold each target stack layer (if not already scaffolded)
    9. Generate cross-layer wiring:
       a. API client for frontend (TypeScript file that calls backend endpoints)
       b. Shared types (TypeScript interfaces matching Go structs)
    10. Show generated files with Rich output (copy UX from mock)
    11. Offer code preview (Syntax highlighted, first 40 lines)
    12. Update pipeline step

    File naming:
    - Backend Go files: handlers/<handler_name>.go (lowercase, underscored)
    - Frontend React files: src/pages/<PageName>.tsx (PascalCase)
    - Store files: internal/store/<store_name>.go

    The generator must produce MULTIPLE files per service group, not just one:
    For users-service backend:
      - handlers/user_handler.go (HTTP handlers)
      - store/user_store.go (DB access)
      - auth/jwt.go (JWT service)
      - auth/middleware.go (Auth middleware)
      - models/user.go (Go structs)
    For users-service frontend:
      - src/pages/LoginPage.tsx
      - src/pages/ProfilePage.tsx
      - src/hooks/useAuth.ts
      - src/api/client.ts (API client)

    Each file is a separate AI call with appropriate context.
    """
    ...
```

### 8.5 Client Component Registry

```python
# In pipeline/generator.py or a separate components.py

def register_components(state: ProjectState, components_path: str) -> None:
    """Register client component library.
    1. Read manifest.json from components_path
    2. Copy to .modernize/components/
    3. Read component docs (markdown files)
    4. Store in state for use during generation

    manifest.json format (see DESIGN.md):
    {
      "frontend": {
        "components": {
          "Button": {"use": "AppleButton", "import": "@apple-ds/components", "docs": "ui/AppleButton.md"},
          ...
        }
      },
      "backend": {
        "patterns": {
          "auth": {"use": "apple-auth-middleware", "docs": "api/auth-middleware.md"},
          ...
        }
      }
    }
    """
    ...

def load_component_context(state: ProjectState, stack_layer: str) -> str:
    """Load component context for a given stack layer.
    Returns a string to include in the AI prompt:
    "CLIENT COMPONENTS:\nUse AppleButton from @apple-ds/components for buttons. ..."
    Returns empty string if no components registered."""
    ...
```

---

## 9. Phase 5: Verifier Module

### 9.1 `pipeline/verifier.py` — Step 7: Verify Behavioral Equivalence

```python
def run_verify(state: ProjectState, service_name: str) -> None:
    """Step 7 — Verify behavioral equivalence.

    Flow:
    1. Verify code was generated for this service
    2. Load locked semantic mapping for this service
    3. Load locked architecture (API contracts) for this service
    4. Load generated code from .modernize/services/<service>/

    Verification has two parts:

    Part A — Locked Mapping Conformance (deterministic, no AI):
    For each business rule in the locked semantic mapping:
      a. Search the generated code for evidence that the rule is implemented
      b. Check: all control flow paths present? All data access operations present?
      c. Mark as CONFORMS or DIVERGES
    This is a text-search / pattern-match operation on the generated code.
    It's NOT running the code — it's checking that the generated code
    contains the expected patterns.

    Search patterns for conformance:
    - For each DataAccess entry: look for SQL or store method that matches table + operation
    - For each ControlFlowRule: look for conditional/error handling that matches
    - For each StateWrite mapped to JWT: look for JWT claim assignment
    - For each business rule with "transactional": look for transaction handling

    Part B — Behavioral Analysis (AI-assisted):
    For each API endpoint in the architecture:
      a. Load the locked mapping for the source function
      b. Load the generated handler code for this endpoint
      c. Send to AI: "Does this generated code implement the locked mapping correctly?
         Report any behavioral differences."
      d. Parse AI response into EndpointVerification
      e. Log AI call via AuditLogger

    5. Compute verdict:
       - All endpoints PASS and all mappings CONFORM → "PASS"
       - Any endpoint NEEDS REVIEW → "PASS (with notes)"
       - Any endpoint FAIL or mapping DIVERGES → "FAIL"
    6. Write .modernize/recordings/<service>/verification-report.json
    7. Display results (Rich tables — copy format from mock)
    8. Update pipeline step

    AI prompt for behavioral analysis:
    System: "You are verifying that generated code correctly implements a locked semantic mapping."
    User:
      "LOCKED MAPPING:\n{serialized mapping}\n\n"
      "GENERATED CODE:\n{generated code}\n\n"
      "API CONTRACT:\n{endpoint definition}\n\n"
      "Does the generated code implement ALL business rules from the mapping?"
      "Check: all control flow paths, all data access, all state management, all error handling."
      "Report status as PASS, FAIL, or NEEDS REVIEW with detailed explanation."
    Output: JSON {"status": "PASS"|"FAIL"|"NEEDS REVIEW", "detail": "..."}
    """
    ...
```

---

## 10. Phase 6: Polish + Auto Mode

### 10.1 `pipeline/runner.py` — Auto Mode (`modernize run --all`)

```python
def run_all(state: ProjectState, auto_approve: bool = True) -> None:
    """Run the full pipeline end-to-end.

    Flow:
    1. Run parse (Step 1)
    2. Run extract (Step 2)
    3. Run document (Step 3)
    4. If auto_approve: approve all modules automatically
       Else: pause and ask user to review
    5. Run lock semantics (Step 5a)
    6. Run architect (Step 5b)
    7. If auto_approve: approve architecture automatically
       Else: pause and ask user to review
    8. Run lock architecture (Step 5d)
    9. For each service group:
       a. Run generate (Step 6)
       b. Run verify (Step 7)
    10. Generate summary report

    Auto-approve behavior:
    - In auto mode, all approvals happen automatically
    - Low-confidence items (below 85%) are flagged in the summary
    - If any verification returns "FAIL", the pipeline STOPS (does not continue to next service)

    Progress display:
    - Use Rich progress bar showing overall pipeline progress
    - Print step headers as each stage begins
    - At the end, print a summary table with all steps and their status
    """
    ...

def run_summary(state: ProjectState) -> None:
    """Post-run summary.
    Display:
    - Overall pipeline status (all steps)
    - Per-service verification verdicts
    - AI usage summary (total calls, tokens, estimated cost)
    - Low-confidence items that need human review
    - Flagged behavioral differences
    """
    ...
```

### 10.2 Human Annotation System

```python
# In modernize.py CLI

@cli.command()
@click.argument("module")
@click.option("--note", required=True)
def annotate(module, note):
    """Add human knowledge to a module.
    Stores in .modernize/annotations/<module>.json.
    Annotations are included in AI context for all subsequent stages.
    Format: {"module": "...", "annotations": [{"note": "...", "by": "...", "at": "..."}]}
    """
    ...
```

### 10.3 Confidence Scoring

Add to `pipeline/extractor.py`:

```python
def compute_confidence(semantic_module: SemanticModule) -> int:
    """Compute overall module confidence score (0-100).
    Formula:
    - Start at 100
    - For each AI-extracted business rule: subtract (100 - rule.confidence) / num_functions
    - For each function with no business rule: subtract 20
    - For each function with empty control flow where conditionals exist in AST: subtract 10
    Round to nearest integer, clamp to 0-100."""
    ...
```

### 10.4 Execution Mode Logic

In each pipeline stage that has a review checkpoint:

```python
def should_auto_proceed(state: ProjectState, confidence: int) -> bool:
    """Determine if auto-proceed is appropriate based on execution mode.
    guided: always False (human must review)
    supervised: True if confidence >= 85
    auto: always True
    """
    migration = state.load()
    mode = migration.get("executionMode", "guided")
    if mode == "auto":
        return True
    elif mode == "supervised":
        return confidence >= 85
    return False
```

---

## 11. Testing Strategy

### 11.1 Test Framework

Use `pytest` with these conventions:
- Tests in `app/tests/`
- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Fixtures in `tests/conftest.py` and `tests/fixtures/`
- Run with: `cd app && python -m pytest`

### 11.2 `tests/conftest.py` — Shared Fixtures

```python
import pytest
from pathlib import Path

@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with .modernize/ structure."""
    state = ProjectState(str(tmp_path))
    state.init("./sample_app", [{"adapter": "react", "role": "frontend"}, {"adapter": "go", "role": "backend"}], "claude", "standard")
    return state

@pytest.fixture
def sample_cf_dir():
    """Path to sample ColdFusion files."""
    return Path(__file__).parent / "fixtures" / "sample_cf"

@pytest.fixture
def mock_provider():
    """A mock AI provider that returns canned responses."""
    class MockProvider(AIProvider):
        def __init__(self):
            self.calls = []  # Record all calls for assertions

        def send_prompt(self, system_prompt, user_prompt, output_format="json"):
            self.calls.append({"system": system_prompt, "user": user_prompt})
            # Return a generic business rule response
            return AIResponse(
                content='{"businessRule": {"name": "Test Rule", "description": "Test description", "confidence": 90}}',
                input_tokens=100, output_tokens=50, model="mock", duration_ms=10
            )

        def get_model_info(self):
            return ModelInfo(name="mock", max_input_tokens=100000, max_output_tokens=8000, provider="mock")

        def estimate_tokens(self, text):
            return len(text) // 4

    return MockProvider()

@pytest.fixture
def sample_ast():
    """A sample UserService AST for testing."""
    # Build the same AST as mock_tool/mock_data/ast_data.py::get_user_service_ast()
    # but using the production ASTComponent dataclass
    ...
```

### 11.3 Critical Test Cases

**ColdFusion Parser** (`tests/integration/test_cf_parser.py`):

```python
def test_parse_user_service(sample_cf_dir):
    """Parse UserService.cfc and verify AST matches expected output."""
    parser = ColdFusionParser()
    ast = parser.parse_file(str(sample_cf_dir / "UserService.cfc"))

    assert ast.name == "UserService"
    assert ast.type == "component"
    assert ast.extends == "BaseService"
    assert len(ast.functions) == 3

    # authenticate function
    auth_fn = ast.functions[0]
    assert auth_fn.name == "authenticate"
    assert auth_fn.access == "public"
    assert auth_fn.return_type == "struct"
    assert len(auth_fn.arguments) == 2
    assert auth_fn.arguments[0].name == "email"
    assert auth_fn.arguments[0].type == "string"
    assert len(auth_fn.queries) == 3  # SELECT + UPDATE (failed) + UPDATE (reset)
    assert auth_fn.queries[0].operation == "SELECT"
    assert "users" in auth_fn.queries[0].tables
    assert auth_fn.queries[0].parameterized == True
    assert len(auth_fn.scope_writes) == 3  # session.userId, session.userRole, session.userEmail
    assert len(auth_fn.conditionals) == 3  # recordCount==0, locked, NOT hashVerify
    assert len(auth_fn.function_calls) >= 1  # hashVerify

def test_parse_order_service(sample_cf_dir):
    """Parse OrderService.cfc and verify transactional detection."""
    parser = ColdFusionParser()
    ast = parser.parse_file(str(sample_cf_dir / "OrderService.cfc"))

    create_order = ast.functions[0]
    assert create_order.name == "createOrder"
    assert create_order.transactional == True  # Wrapped in <cftransaction>

    cancel_order = ast.functions[2]
    assert cancel_order.name == "cancelOrder"
    assert cancel_order.transactional == True

def test_parse_login_template(sample_cf_dir):
    """Parse login.cfm and verify template parsing."""
    parser = ColdFusionParser()
    ast = parser.parse_file(str(sample_cf_dir / "login.cfm"))

    assert ast.name == "login"
    assert ast.type == "template"
    assert len(ast.functions) == 1
    assert ast.functions[0].name == "(page_logic)"
    # Should detect createObject and userService.authenticate calls
    call_targets = [fc.target for fc in ast.functions[0].function_calls]
    assert "createObject" in call_targets or "userService.authenticate" in call_targets
```

**SQL Extractor** (`tests/unit/test_sql_extractor.py`):

```python
def test_extract_select():
    ext = SQLExtractor()
    result = ext.extract("SELECT id, email, password_hash FROM users WHERE email = ?")
    assert result["operation"] == "SELECT"
    assert "users" in result["tables"]
    assert "id" in result["columns"]

def test_extract_insert():
    ext = SQLExtractor()
    result = ext.extract("INSERT INTO orders (user_id, total, status) VALUES (?, ?, 'pending')")
    assert result["operation"] == "INSERT"
    assert "orders" in result["tables"]

def test_normalize_cf_sql():
    ext = SQLExtractor()
    raw = 'SELECT id FROM users WHERE email = <cfqueryparam cfsqltype="cf_sql_varchar" value="#arguments.email#">'
    normalized = ext.normalize_cf_sql(raw)
    assert "<cfqueryparam" not in normalized
    assert "?" in normalized
```

**State Management** (`tests/unit/test_state.py`):

```python
def test_init_creates_directories(tmp_path):
    state = ProjectState(str(tmp_path))
    state.init("./src", [{"adapter": "react", "role": "frontend"}], "claude", "standard")
    assert (tmp_path / ".modernize").exists()
    assert (tmp_path / ".modernize" / "ast").exists()
    assert (tmp_path / ".modernize" / "migration.json").exists()

def test_atomic_write(tmp_path):
    """Verify writes are atomic (no partial files on interruption)."""
    state = ProjectState(str(tmp_path))
    state.init("./src", [{"adapter": "react", "role": "frontend"}], "claude", "standard")
    state.write_artifact("ast", "test.json", {"key": "value"})
    data = state.read_artifact("ast", "test.json")
    assert data["key"] == "value"

def test_step_tracking(tmp_project):
    assert tmp_project.get_step_status("parse") == "pending"
    tmp_project.update_step("parse", "completed", filesCount=3)
    assert tmp_project.get_step_status("parse") == "completed"
```

**Sanitizer** (`tests/unit/test_sanitizer.py`):

```python
def test_sanitize_datasource():
    s = Sanitizer()
    text = 'datasource="prod_oracle_crm"'
    sanitized, redaction_map = s.sanitize(text)
    assert "prod_oracle_crm" not in sanitized
    assert "[DATASOURCE_" in sanitized

def test_stable_placeholders():
    """Same value should always get the same placeholder."""
    s = Sanitizer()
    t1, _ = s.sanitize('password="secret123"')
    t2, _ = s.sanitize('password="secret123"')
    assert t1 == t2

def test_sanitize_dict():
    s = Sanitizer()
    data = {"dsn": "prod_oracle", "sql": "SELECT * FROM users"}
    sanitized, _ = s.sanitize_dict(data)
    assert "prod_oracle" not in str(sanitized)
```

**Lock Integrity** (`tests/unit/test_locker.py`):

```python
def test_lock_checksum_verification(tmp_project):
    """Verify that tampering with a locked file is detected."""
    # ... set up locked semantics ...
    assert verify_lock_integrity(tmp_project) == True

    # Tamper with the lock file
    lock = tmp_project.read_artifact("locked", "semantic-lock.json")
    lock["modules"]["UserService"]["semantics"]["functions"][0]["name"] = "TAMPERED"
    tmp_project.write_artifact("locked", "semantic-lock.json", lock)

    assert verify_lock_integrity(tmp_project) == False
```

**Full Pipeline** (`tests/integration/test_pipeline_flow.py`):

```python
def test_full_pipeline_with_mock_provider(tmp_path, sample_cf_dir, mock_provider):
    """Run the entire pipeline from init to verify with a mock AI provider.
    This is the end-to-end integration test."""
    # 1. Init
    # 2. Parse (uses real CF parser)
    # 3. Extract (uses mock provider for AI calls)
    # 4. Approve all
    # 5. Lock semantics
    # 6. Architect (uses mock provider)
    # 7. Approve + lock architecture
    # 8. Generate (uses mock provider)
    # 9. Verify (uses mock provider)
    # Assert: all steps completed, all artifacts exist
    ...
```

### 11.4 pytest Configuration

`app/pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
markers =
    integration: marks tests as integration tests (may be slower)
    unit: marks tests as unit tests
```

---

## 12. Error Handling Contract

Every pipeline step must follow this error handling contract:

### 12.1 Precondition Checks

Every `run_*` function checks its preconditions first:

```python
def run_extract(state: ProjectState) -> None:
    if not state.is_initialized:
        raise StateError("Project not initialized. Run 'modernize init' first.")
    if state.get_step_status("parse") != "completed":
        raise PipelineError("extract", "AST not parsed yet. Run 'modernize parse' first.")
```

### 12.2 AI Call Failures

AI calls can fail. Handle gracefully:

```python
try:
    response = provider.send_prompt(system_prompt, user_prompt, output_format="json")
    result = json.loads(response.content)
except ProviderError as e:
    if e.retryable:
        # Retry once after 2-second delay
        time.sleep(2)
        response = provider.send_prompt(system_prompt, user_prompt, output_format="json")
        result = json.loads(response.content)
    else:
        # Log failure, use fallback
        console.print(f"[yellow]Warning: AI call failed for {module_name}: {e}[/]")
        result = fallback_result
except json.JSONDecodeError:
    # AI returned non-JSON response
    console.print(f"[yellow]Warning: AI returned invalid JSON for {module_name}[/]")
    result = fallback_result
```

### 12.3 File Parse Failures

If a ColdFusion file fails to parse:
1. Log the error with Rich: `console.print(f"[red]Error parsing {filename}: {e}[/]")`
2. Skip the file and continue with others
3. Report all skipped files at the end of the parse step
4. Only fail the entire step if ALL files fail

### 12.4 CLI Error Display

Wrap each CLI command handler in a try/except that catches `ModernizeError`:

```python
@cli.command()
def parse():
    try:
        run_parse(get_state())
    except ModernizeError as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1)
```

---

## 13. Implementation Order Within Each Phase

When implementing, follow this order within each phase. Each item should be a separate commit.

### Phase 1 (Foundation):
1. `core/errors.py` — exception hierarchy
2. `core/models.py` — all dataclasses with to_dict/from_dict
3. `core/state.py` — ProjectState
4. `core/sanitizer.py` — Sanitizer
5. `core/audit.py` — AuditLogger
6. `providers/base.py` — AIProvider interface
7. `providers/claude.py` — Claude adapter
8. `providers/openai_provider.py` — OpenAI adapter
9. `providers/gemini.py` — Gemini adapter
10. `providers/__init__.py` — factory function
11. `core/chunker.py` — Chunker
12. `core/context_assembler.py` — ContextAssembler
13. `core/aggregator.py` — ResultAggregator
14. `agents/loader.py`, `agents/resolver.py`, `agents/registry.py`
15. `modernize.py` — CLI skeleton with `init`, `status`, `audit` commands
16. Tests for all of the above

### Phase 2 (Parser + Extractor):
1. `adapters/source/base.py` — SourceAdapter interface
2. `adapters/source/coldfusion/sql_extractor.py` — SQL parsing
3. `adapters/source/coldfusion/parser.py` — ColdFusion parser
4. `adapters/source/coldfusion/adapter.py` — ColdFusionAdapter
5. Agent YAML files (all 7)
6. `pipeline/parser.py` — Step 1
7. `pipeline/extractor.py` — Step 2
8. `pipeline/documenter.py` — Step 3
9. `pipeline/reviewer.py` — Step 4
10. CLI commands: `parse`, `extract`, `document`, `review`, `correct`, `approve`
11. Tests: parser tests (critical), extractor tests, CLI integration tests

### Phase 3 (Lock + Architect):
1. `pipeline/locker.py` — lock/unlock/verify
2. `pipeline/architect.py` — architecture design
3. CLI commands: `lock`, `unlock`, `architect`, `review architect`, `approve architect`
4. Tests: lock integrity, architecture generation

### Phase 4 (Generator):
1. `adapters/target/base.py` — TargetAdapter interface
2. `adapters/target/react/` — React adapter + scaffolder + conventions
3. `adapters/target/go/` — Go adapter + scaffolder + conventions
4. `pipeline/generator.py` — Step 6
5. Client component registry
6. CLI commands: `generate`, `review generate`, `components register`
7. Tests: generation with mock provider

### Phase 5 (Verifier):
1. `pipeline/verifier.py` — Step 7
2. CLI command: `verify`
3. Tests: verification logic

### Phase 6 (Polish):
1. `pipeline/runner.py` — auto mode (`run --all`, `summary`)
2. Annotation system
3. Confidence scoring
4. Execution mode logic (guided/supervised/auto)
5. Redact commands (`redact review`, `redact add`, `redact remove`, `redact add-pattern`)
6. CLI commands: `run`, `summary`, `annotate`
7. Full end-to-end integration test

---

## Appendix A: ColdFusion Agent YAML Templates

### cf-query-agent.yaml

```yaml
name: cf-query-agent
appliesTo: ["cfquery", "cfstoredproc", "cfprocparam", "queryExecute"]

systemPrompt: |
  You are an expert in ColdFusion database access patterns. You understand
  cfquery tag syntax, datasource architecture, cfqueryparam for SQL injection
  prevention, query-of-queries (in-memory result set queries), stored procedure
  calls via cfstoredproc, and the queryExecute() function in CFScript.

  When analyzing database access:
  - Identify the business purpose of each query
  - Note parameterization status (cfqueryparam = safe, string interpolation = unsafe)
  - Identify table relationships from JOINs
  - Note transaction boundaries (cftransaction)
  - Flag any SQL injection risks

conventions: |
  - <cfquery name="qUsers" datasource="#dsn#"> defines a named query
  - <cfqueryparam cfsqltype="cf_sql_varchar" value="#id#"> = parameterized binding
  - Query-of-queries: SELECT from an existing query result set (in-memory join)
  - returntype="query" on CFC methods means it returns a query result set
  - Datasource names reference JNDI or CF Admin configured DSNs
  - <cftransaction> wraps multiple queries in a database transaction
  - result="varName" on cfquery captures metadata (generatedKey, recordCount)

outputSchema:
  queries:
    - name: string
      sql: string
      tables: [string]
      operation: string
      parameterized: boolean
      businessPurpose: string
      confidence: number

stages: [extract, generate, verify]
```

### cf-ui-agent.yaml

```yaml
name: cf-ui-agent
appliesTo: ["cfm", "cfoutput", "cfform", "cfinput"]

systemPrompt: |
  You are an expert in ColdFusion template rendering and UI patterns. You understand
  CFM templates that mix HTML with CF tags, cfoutput for variable display, cfform
  for form generation, conditional rendering with cfif, and the relationship between
  templates and CFC components.

  When analyzing UI templates:
  - Identify the page's purpose and user flow
  - Map form fields to their validation rules
  - Note navigation links and redirects
  - Identify error display patterns
  - Map component instantiation (createObject) to service dependencies

conventions: |
  - CFM files are templates that output HTML
  - <cfoutput>#variable#</cfoutput> renders a variable
  - <cfform> generates an HTML form with optional JS validation
  - <cfinput> generates form inputs with validation attributes
  - <cflocation url="..."> redirects the browser
  - <cfif isDefined("errorMessage")> is conditional rendering
  - Templates often contain both processing logic and HTML in the same file

outputSchema:
  uiAnalysis:
    pagePurpose: string
    formFields: [{name: string, type: string, validation: string}]
    navigation: [{target: string, condition: string}]
    errorHandling: string
    confidence: number

stages: [extract, generate, verify]
```

### cf-auth-agent.yaml

```yaml
name: cf-auth-agent
appliesTo: ["session", "cflogin", "cflogout"]

systemPrompt: |
  You are an expert in ColdFusion authentication and session management. You understand
  CF's session scope, application scope, cflogin/cflogout tags, role-based access
  via IsUserInRole(), and the session lifecycle.

  When analyzing auth patterns:
  - Map all session state reads and writes
  - Identify the authentication flow (login, logout, session check)
  - Note role-based access control patterns
  - Identify session timeout handling
  - Map to modern equivalents (JWT claims, middleware)

conventions: |
  - session.userId, session.userRole = common auth state
  - <cflogin>/<cflogout> are built-in auth tags (rarely used in modern CF)
  - Most apps use manual session management via <cfset session.xxx>
  - hashVerify(plaintext, hash) verifies bcrypt passwords
  - IsUserInRole("admin") checks role-based access

outputSchema:
  authAnalysis:
    sessionState: [{key: string, purpose: string, writtenBy: string}]
    authFlow: string
    roles: [string]
    confidence: number

stages: [extract, generate, verify]
```

---

## Appendix B: Key Behavioral Notes for Implementors

1. **JSON output keys are camelCase** — every `to_dict()` must convert snake_case fields to camelCase. This is critical for compatibility with the design doc examples and the mock tool output.

2. **The ColdFusion parser is regex-based, not tree-sitter** — see dependency note in Section 2. The regex approach works because ColdFusion tags are XML-like. If tree-sitter-cfml becomes available later, the parser can be swapped inside the adapter without changing the interface.

3. **AI calls must always have fallbacks** — if the AI fails, the pipeline must not crash. Use deterministic fallbacks (e.g., function name as business rule name).

4. **Locks are checksummed** — the semantic lock and architecture lock include SHA-256 checksums. The `verify_lock_integrity()` function recomputes and compares. This is a security feature to detect tampering.

5. **Corrections modify the semantic model** — when `modernize correct` is called, update BOTH the corrections file (for audit trail) and the actual semantic JSON (so downstream steps see the correction). The mock tool only writes corrections; production must do both.

6. **Provider packages are imported lazily** — `import anthropic` only happens inside `ClaudeProvider.__init__()`, not at module level. This allows users to install only the provider they need.

7. **The `run --all` auto mode stops on verification failure** — auto mode runs everything but respects verification. If `verify` returns FAIL for any service, the pipeline halts. Low-confidence items below 85% are flagged in the summary but don't stop the pipeline.

8. **File writes are atomic** — use write-to-temp-then-rename pattern for all JSON writes. This prevents corruption if the process is killed mid-write.

9. **The architecture blueprint is split into multiple markdown files** — one index, one per service group, one for cross-cutting. This enables independent review. See mock_tool/mock_data/architecture_data.py for exact formats.

10. **The generator produces multiple files per service** — not just handlers. It must also generate store/DB access, models/structs, auth middleware, and API client code. Each is a separate AI call.
