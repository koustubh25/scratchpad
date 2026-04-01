# Implementation Plan — Modernize CLI (v2 — Complete)

> **Audience**: An AI coding assistant (Sonnet 4.5 or equivalent) that will implement this plan step by step.
> **Source of truth**: `DESIGN-v2.md` in this repo. This plan translates that design into exact code specifications.
> **Reference implementation**: `mock_tool/` contains a working demo with mock data. Use it to understand the UX, data shapes, and CLI flow — but do NOT copy its code. The production tool replaces mock data with real logic.
> **Supersedes**: `IMPLEMENTATION-PLAN.md` (the original v2 plan). This file is the complete, up-to-date version incorporating all 28 design risks, the architecture stage split, and new infrastructure.

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
14. [CLI Command Reference](#14-cli-command-reference)

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
│   ├── __init__.py                 # Shared console instance (Rich)
│   ├── models.py                   # All dataclasses (AST, semantic, locks, checkpoints, etc.)
│   ├── state.py                    # ProjectState — .modernize/ directory management
│   ├── schemas.py                  # JSON Schema definitions for validation
│   ├── sanitizer.py                # Data redaction engine
│   ├── chunker.py                  # AST-node-level chunking for context windows
│   ├── context_assembler.py        # Build context packets for AI calls
│   ├── aggregator.py               # Merge multi-chunk AI results
│   ├── audit.py                    # AI call audit logging + hash chain (Risk 26)
│   ├── confidence.py               # Confidence scoring module (Risk 5)
│   ├── checkpoint.py               # Pipeline checkpoint/resume (Risk 15)
│   ├── cost.py                     # Cost estimation + budget tracking (Risk 16)
│   ├── encoding.py                 # File encoding detection + normalization (Risk 23)
│   ├── file_lock.py                # Advisory file locking for concurrency (Risk 28)
│   ├── schema_version.py           # Artifact schema versioning + migration (Risk 20)
│   ├── errors.py                   # Custom exception hierarchy
│   └── utils.py                    # to_camel_case, hash helpers, atomic write
│
├── providers/                      # AI provider adapters
│   ├── __init__.py                 # create_provider() factory
│   ├── base.py                     # Abstract AIProvider interface
│   ├── claude.py                   # Anthropic Claude adapter
│   ├── openai_provider.py          # OpenAI adapter
│   └── gemini.py                   # Google Gemini adapter
│
├── pipeline/                       # Pipeline stage modules
│   ├── __init__.py
│   ├── parser.py                   # Step 1: Parse to AST + config capture + asset scan
│   ├── extractor.py                # Step 2: Extract semantics
│   ├── documenter.py               # Step 3: Generate review docs
│   ├── reviewer.py                 # Step 4: Interactive review + corrections + conflicts
│   ├── locker.py                   # Step 5a/5f/5g: Lock mappings (per-module granularity)
│   ├── architect.py                # Step 5b/5c/5d: Existing analysis + target stack + target design
│   ├── generator.py                # Step 6: Generate code + URL mappings + asset copy
│   ├── recorder.py                 # Record HTTP traffic from legacy app (Risk 17)
│   ├── verifier.py                 # Step 7: Verify equivalence + replay + conformance
│   ├── runner.py                   # Auto mode: run full pipeline
│   ├── reporter.py                 # Pipeline observability (status, report)
│   └── import_schema.py            # Import stored procedures from DB catalog (Risk 13)
│
├── adapters/                       # Language-specific adapters
│   ├── __init__.py
│   ├── source/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract SourceAdapter interface (updated)
│   │   └── coldfusion/
│   │       ├── __init__.py
│   │       ├── adapter.py          # ColdFusionAdapter — implements SourceAdapter
│   │       ├── parser.py           # tree-sitter walker → semantic AST
│   │       ├── sql_extractor.py    # SQL string parsing (uses sqlglot)
│   │       ├── config_parser.py    # Application.cfc / web.xml config capture (Risk 18)
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
│       │   ├── adapter.py          # ReactAdapter
│       │   ├── scaffolder.py       # Vite + React project setup
│       │   └── conventions.py      # React conventions
│       └── go/
│           ├── __init__.py
│           ├── adapter.py          # GoAdapter
│           ├── scaffolder.py       # Go module + Chi router setup
│           └── conventions.py      # Go conventions
│
├── agents/                         # Agent system
│   ├── __init__.py
│   ├── loader.py                   # Load agent YAML definitions
│   ├── resolver.py                 # Match AST nodes → agents via appliesTo rules
│   └── registry.py                 # Global registry of loaded agents
│
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Shared fixtures
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
    │   ├── test_sql_extractor.py
    │   ├── test_confidence.py
    │   ├── test_checkpoint.py
    │   ├── test_cost.py
    │   ├── test_encoding.py
    │   ├── test_file_lock.py
    │   ├── test_schema_version.py
    │   └── test_hash_chain.py
    ├── integration/
    │   ├── __init__.py
    │   ├── test_cf_parser.py       # ColdFusion adapter end-to-end
    │   ├── test_pipeline_flow.py   # Full pipeline from parse → verify
    │   ├── test_cli.py             # Click CLI integration tests
    │   ├── test_incremental.py     # Incremental processing (Risk 11)
    │   └── test_concurrent.py      # Concurrent access (Risk 28)
    └── fixtures/
        ├── sample_cf/              # ColdFusion fixture files
        │   ├── UserService.cfc
        │   ├── OrderService.cfc
        │   ├── login.cfm
        │   └── Application.cfc     # Config fixture (Risk 18)
        ├── expected_ast/           # Expected AST JSON output
        ├── expected_semantics/     # Expected semantic JSON
        └── encoding/               # Files in various encodings (Risk 23)
            ├── latin1_file.cfc
            └── utf8_bom_file.cfc
```

### Files that should NOT be created

- No `setup.py` or `pyproject.toml` — use `requirements.txt` only
- No `Makefile` — keep it simple
- No Docker files — local-first tool
- No `.env` files — API keys via CLI options or environment variables
- No GUI/dashboard — CLI-only (out of scope)

---

## 2. Dependencies

Create `app/requirements.txt`:

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

# Encoding detection (Risk 23)
charset-normalizer>=3.3,<4.0

# Database catalog import (Risk 13)
sqlalchemy>=2.0,<3.0

# Utilities
pyyaml>=6.0,<7.0
jsonschema>=4.20,<5.0

# Testing (dev)
pytest>=8.0,<9.0
pytest-tmp-files>=0.0.2
```

**Important notes:**

- `tree-sitter-cfml`: If not available on PyPI, write a fallback regex-based ColdFusion parser in `adapters/source/coldfusion/parser.py`. ColdFusion's XML-like tag syntax is regular enough for regex parsing.
- `google-genai`: Google's unified SDK. If import issues, use `google-generativeai` instead.
- `charset-normalizer`: Pure Python, no external deps. Used for encoding detection (Risk 23).
- `sqlalchemy`: Only used by `import-schema` command (Risk 13). Imported lazily.
- All AI provider packages imported lazily — only when user selects that provider.

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

Every dataclass must have `to_dict()` and `from_dict()` class methods. Do NOT use `dataclasses.asdict()`.

```python
@dataclass
class ASTQuery:
    name: str
    sql: str
    tables: list[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "sql": self.sql,
            "tables": self.tables,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ASTQuery:
        return cls(
            name=data["name"],
            sql=data["sql"],
            tables=data["tables"],
        )
```

### 3.4 Error Handling Pattern

Custom exception hierarchy in `core/errors.py`:

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

class ConcurrencyError(ModernizeError):
    """Another process holds the pipeline lock (Risk 28)."""
    def __init__(self, lock_holder: str, lock_file: str):
        self.lock_holder = lock_holder
        self.lock_file = lock_file
        super().__init__(f"Pipeline locked by {lock_holder}. Lock file: {lock_file}")

class EncodingError(ModernizeError):
    """File encoding detection failed (Risk 23)."""
    pass

class SchemaVersionError(ModernizeError):
    """Artifact schema version mismatch (Risk 20)."""
    def __init__(self, expected: str, found: str):
        self.expected = expected
        self.found = found
        super().__init__(f"Schema version mismatch: expected {expected}, found {found}")
```

### 3.5 Console Output Pattern

All user-facing output uses `rich`. Shared console in `core/__init__.py`:

```python
# core/__init__.py
from rich.console import Console
console = Console()
```

Import everywhere: `from core import console`. Do NOT create multiple Console instances.

### 3.6 Abstract Base Classes

Use `abc.ABC` and `@abstractmethod` for all plugin interfaces.

### 3.7 No Global Mutable State

All state flows through function arguments. Only exception: shared `console` instance.

### 3.8 File I/O Pattern

All file reads/writes go through `ProjectState`. No direct `open()` calls in pipeline modules. Exception: adapter code reading source files during parsing.

### 3.9 Atomic Writes (Risk 28)

All JSON writes use write-to-temp-then-rename:

```python
# In core/utils.py
import os
import tempfile
import json

def atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically. Prevents corruption from concurrent access or crashes."""
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp_path, str(path))
    except:
        os.unlink(tmp_path)
        raise
```

### 3.10 JSON Key Convention

All JSON files use **camelCase** keys. Python uses **snake_case**. The `to_dict()` methods must convert.

```python
# core/utils.py
def to_camel_case(snake_str: str) -> str:
    parts = snake_str.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])
```

### 3.11 Schema Version Stamping (Risk 20)

Every artifact written to `.modernize/` includes schema version:

```python
# core/schema_version.py
SCHEMA_VERSION = "2.1"
CLI_VERSION = "0.1.0"

def stamp_artifact(data: dict) -> dict:
    """Add schema version + CLI version to an artifact dict."""
    data["schemaVersion"] = SCHEMA_VERSION
    data["generatedBy"] = f"modernize@{CLI_VERSION}"
    return data
```

---

## 4. Data Models (Core Types)

File: `app/core/models.py`

This is the most critical file. Every downstream module depends on these types.

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
    parameterized: bool = True

@dataclass
class ASTArgument:
    name: str
    type: str                       # "string", "numeric", "array", "struct", "query", "boolean", "any"
    required: bool = True
    default: str | None = None

@dataclass
class ASTScopeWrite:
    scope: str                      # "session", "application", "variables", "request", "form"
    key: str
    value: str = ""

@dataclass
class ASTConditional:
    condition: str                  # Human-readable condition description
    action: str                     # "throw", "return", "set", "redirect", "process_form"
    detail: str = ""

@dataclass
class ASTFunctionCall:
    target: str                     # "hashVerify", "userService.authenticate"
    args: list[str] = field(default_factory=list)

@dataclass
class ASTFunction:
    name: str                       # "(page_logic)" for template-level code
    access: str                     # "public", "private", "remote", "package"
    return_type: str
    arguments: list[ASTArgument] = field(default_factory=list)
    queries: list[ASTQuery] = field(default_factory=list)
    scope_writes: list[ASTScopeWrite] = field(default_factory=list)
    conditionals: list[ASTConditional] = field(default_factory=list)
    function_calls: list[ASTFunctionCall] = field(default_factory=list)
    returns: dict = field(default_factory=dict)
    transactional: bool = False
    locale_sensitive: bool = False  # Risk 24: uses LSDateFormat, LSNumberFormat, etc.

    # to_dict(), from_dict()

@dataclass
class ASTProperty:
    name: str
    type: str
    scope: str                      # "variables", "this"
    value: str = ""

@dataclass
class UnparsedBlock:
    """Risk 21: Region that tree-sitter could not parse."""
    start_line: int
    end_line: int
    raw_text: str
    reason: str                     # "Unrecognized tag structure: <cfmodule>"

@dataclass
class ASTComponent:
    name: str                       # "UserService", "login"
    file: str                       # "UserService.cfc", "login.cfm"
    type: str                       # "component" (CFC) or "template" (CFM)
    extends: str = ""
    properties: list[ASTProperty] = field(default_factory=list)
    functions: list[ASTFunction] = field(default_factory=list)
    # Risk 21: graceful degradation
    parse_status: str = "complete"  # "complete" | "partial" | "failed"
    unparsed_blocks: list[UnparsedBlock] = field(default_factory=list)
    coverage_percent: float = 100.0
    # Risk 22: adapter version stamping
    adapter_version: str = ""       # "coldfusion-adapter@1.0.0+sha256:abc..."
    # Risk 23: encoding metadata
    source_encoding: str = "utf-8"
    normalized_to: str = "utf-8"
    encoding_confidence: float = 1.0
    # Risk 11: incremental processing
    source_hash: str = ""           # SHA-256 of source file at parse time

    # to_dict(), from_dict()
```

### 4.2 Semantic Models (Step 2 output)

```python
@dataclass
class BusinessRule:
    name: str
    description: str
    source: str                     # "ai" | "deterministic" | "human"
    confidence: int = 90

@dataclass
class DataAccess:
    table: str
    operation: str
    columns: list[str] = field(default_factory=list)
    filter: str = ""
    purpose: str = ""
    parameterized: bool = True

@dataclass
class StateWrite:
    scope: str
    key: str
    condition: str = ""

@dataclass
class ControlFlowRule:
    condition: str
    action: str

@dataclass
class ExternalDependency:
    """Risk 10: External dependencies without source."""
    dep_type: str                   # "com" | "stored-proc" | "http-api" | "java"
    ref: str                        # "Word.Application", "sp_GetUser", etc.
    source: str = "stub"            # "stub" | "database-catalog"
    call_signature: str = ""
    parameters: list[dict] = field(default_factory=list)

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
    locale_sensitive: bool = False  # Risk 24
    locale_functions: list[str] = field(default_factory=list)  # ["LSDateFormat", "LSNumberFormat"]
    external_deps: list[ExternalDependency] = field(default_factory=list)  # Risk 10

    # to_dict() outputs camelCase keys
    # from_dict() accepts camelCase keys

@dataclass
class UIElements:
    form: dict | None = None
    links: list[str] = field(default_factory=list)
    error_display: str = ""

@dataclass
class SemanticModule:
    module: str
    source: str
    functions: list[SemanticFunction] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    complexity: str = "low"         # "low" | "medium" | "high"
    ui_elements: UIElements | None = None
    approved: bool = False
    approved_by: str | None = None
    # Risk 11: hash chain for incremental
    source_hash: str = ""           # Hash of source file
    ast_hash: str = ""              # Hash of AST file this was extracted from
    # Risk 19: reviewer assignment
    primary_reviewer: str | None = None  # Assigned reviewer email
    review_status: str = "pending"  # "pending" | "in-review" | "approved" | "needs-re-review"

    # to_dict() / from_dict()

@dataclass
class CrossModuleData:
    dependency_graph: dict[str, dict[str, list[str]]]
    table_ownership: dict[str, list[str]]
    shared_state: dict[str, dict[str, list[str]]]
    # Risk 1: consistency check results
    consistency_report: list[dict] = field(default_factory=list)

    # to_dict() / from_dict()
```

### 4.3 Config & Asset Inventory Models (Risk 18, 25)

```python
@dataclass
class DatasourceConfig:
    name: str
    driver: str                     # "sqlserver", "mysql", "oracle"
    host: str                       # "[REDACTED]" after sanitization
    database: str
    source: str                     # "Application.cfc:12"

@dataclass
class SessionConfig:
    timeout: str
    storage: str                    # "memory", "database", "j2ee"
    source: str

@dataclass
class ConfigInventory:
    """Risk 18: Captured config/environment settings."""
    datasources: list[DatasourceConfig] = field(default_factory=list)
    session: SessionConfig | None = None
    smtp: dict | None = None
    feature_flags: list[dict] = field(default_factory=list)
    custom_settings: list[dict] = field(default_factory=list)
    # Risk 24: locale/timezone
    locale: str = ""                # "en_US"
    timezone: str = ""              # "America/New_York"
    jvm_locale: str = ""

    # to_dict() / from_dict()

@dataclass
class StaticAsset:
    """Risk 25: Non-code static asset."""
    path: str
    asset_type: str                 # "image", "css", "javascript-library", "email-template", "font", "other"
    size: str
    referenced_by: list[str] = field(default_factory=list)
    action: str = "review"          # "copy" | "replace" | "migrate" | "review"
    note: str = ""

@dataclass
class AssetInventory:
    assets: list[StaticAsset] = field(default_factory=list)
    summary: dict = field(default_factory=dict)  # {"copy": N, "replace": N, "migrate": N, "review": N}

    # to_dict() / from_dict()
```

### 4.4 Architecture Models (Step 5b-5d)

```python
@dataclass
class TargetStackMapping:
    adapter: str                    # "react", "go"
    components: list[str]

@dataclass
class ServiceGroup:
    name: str
    modules: list[str]
    shared_tables: list[str]
    reason: str
    target_stack: dict[str, TargetStackMapping]

@dataclass
class APIEndpoint:
    path: str                       # "POST /api/auth/login"
    request: dict
    response: dict
    source: str                     # "UserService.authenticate"

@dataclass
class APIContract:
    service: str
    endpoints: list[APIEndpoint]

@dataclass
class ComponentRoute:
    source: str                     # "UserService.authenticate"
    target: str                     # "UserHandler.Login"
    stack_layer: str                # "backend" | "frontend" | "workers"
    agent: str                      # "logic" | "ui" | "db" | "auth" | etc.

@dataclass
class URLMapping:
    """Risk 27: Legacy URL → new URL rewrite rule."""
    legacy: str                     # "/index.cfm?action=users.list"
    new: str | None                 # "/api/users" or None for deprecated
    method: str = "GET"
    rewrite_type: str = "permanent" # "permanent" | "deprecated"
    query_params: dict = field(default_factory=dict)
    body_transform: str = ""        # "form-to-json" or ""

@dataclass
class ArchitectureDecision:
    service_groups: list[ServiceGroup]
    api_contracts: list[APIContract]
    component_routing: list[ComponentRoute]
    data_mapping: dict[str, str]    # {"session.userId": "JWT claim: sub"}
    url_mappings: list[URLMapping] = field(default_factory=list)  # Risk 27

    # to_dict() / from_dict()
```

### 4.5 Lock Models (Step 5a/5f/5g)

```python
@dataclass
class LockedModule:
    status: str                     # "locked" | "needs-re-review" | "stale"
    approved_by: str
    approved_at: str
    semantics: dict
    corrections: list[dict]
    checksum: str                   # "sha256:abc123..."
    source_hash: str = ""           # Risk 11: hash of source file at lock time
    ast_hash: str = ""              # Risk 11: hash of AST at lock time

@dataclass
class SemanticLock:
    lock_version: str               # "1.0"
    locked_at: str
    locked_by: str
    modules: dict[str, LockedModule]
    cross_module: dict | None = None
    schema_version: str = ""        # Risk 20

@dataclass
class ArchitectureLock:
    lock_type: str                  # "architecture"
    lock_version: str
    locked_at: str
    locked_by: str
    target_stack: dict              # {"frontend": "react", "backend": "go", "chosenBy": "...", "chosenAt": "..."}
    architecture: dict              # Full architecture decisions
    checksum: str
    schema_version: str = ""        # Risk 20

@dataclass
class LockManifest:
    lock_type: str                  # "semantic"
    version: str
    locked_at: str
    module_count: int
    checksums: dict[str, str]       # {module_name: checksum}
    architecture_lock: dict | None = None
    fully_locked: bool = False
```

### 4.6 Agent Definition Model

```python
@dataclass
class AgentDefinition:
    name: str                       # "cf-logic-agent"
    applies_to: list[str]           # ["cffunction", "cfcomponent"]
    system_prompt: str
    conventions: str
    output_schema: dict
    stages: list[str]               # ["extract", "generate", "verify"]
    advisory: bool = False          # v3 only — always False in v2

    @classmethod
    def from_yaml(cls, path: str) -> AgentDefinition:
        """Load from a YAML file."""
        ...
```

### 4.7 Context Packet Model

```python
@dataclass
class ContextPacket:
    agent: AgentDefinition
    task_instruction: str
    input_data: str
    prior_results: str              # Risk 4: prior chunk context
    output_schema: dict
    token_budget: int
    metadata: dict = field(default_factory=dict)
```

### 4.8 Checkpoint Model (Risk 15)

```python
@dataclass
class Checkpoint:
    step: str                       # "extract", "generate", etc.
    started_at: str                 # ISO 8601
    status: str                     # "in-progress" | "completed" | "failed"
    completed: list[str]            # Module/service names done
    failed: list[dict]              # [{"module": "...", "error": "..."}]
    remaining: list[str]            # Modules not yet processed
    current_module: str = ""        # In-progress when interrupted
    total_cost: float = 0.0         # Cumulative cost so far

    # to_dict() / from_dict()
```

### 4.9 Audit Entry Model (Risk 26)

```python
@dataclass
class AuditEntry:
    sequence: int
    timestamp: str                  # ISO 8601
    action: str                     # "ai_call", "approve_semantics", "lock_semantics", etc.
    module: str
    actor: str                      # "ai:claude-sonnet-4-6" or "john@legacy-team.com"
    details: dict
    previous_hash: str              # SHA-256 of previous entry
    entry_hash: str = ""            # SHA-256 of this entry (computed on write)

    # to_dict() / from_dict()
```

### 4.10 Recording Model (Risk 17)

```python
@dataclass
class RecordedPair:
    request: dict                   # {"method": "GET", "path": "/api/users/42", "headers": {...}}
    legacy_response: dict           # {"status": 200, "body": {...}, "latencyMs": 120}
    new_response: dict | None = None
    diff_result: dict | None = None # {"status": "PASS"|"FAIL"|"DRIFT", "detail": "..."}
    recorded_at: str = ""

@dataclass
class ReplayResult:
    total_requests: int
    passed: int
    acceptable_drift: int
    failed: int
    failures: list[dict]            # Details of failed replays
```

### 4.11 Generation Baseline Model (Risk 12)

```python
@dataclass
class GenerationManifest:
    """Tracks per-file generation state for human edit detection."""
    service: str
    files: dict[str, dict]          # {filepath: {"baselineHash": "...", "currentHash": "...", "status": "generated"|"modified"|"manually-maintained"}}
```

### 4.12 File Lock Model (Risk 28)

```python
@dataclass
class PipelineLock:
    step: str
    scope: str                      # "global" | service-group name
    holder: str                     # Username
    pid: int                        # Process ID
    acquired_at: str                # ISO 8601
    lock_file: str                  # Path to lock file
```

### 4.13 Correction with Conflict Tracking (Risk 19)

```python
@dataclass
class Correction:
    field: str                      # "authenticate.businessRule.description"
    original: str
    corrected: str
    by: str                         # "john@legacy-team.com"
    at: str                         # ISO 8601
    reason: str = ""

@dataclass
class CorrectionConflict:
    field: str
    reviewer_a: dict                # {"value": "...", "by": "..."}
    reviewer_b: dict
    resolution: str = ""
    resolved_by: str = ""
    resolved_at: str = ""
```

### 4.14 Verification Models

```python
@dataclass
class EndpointVerification:
    endpoint: str
    source: str
    status: str                     # "PASS" | "FAIL" | "NEEDS REVIEW"
    detail: str

@dataclass
class MappingConformance:
    rule: str
    status: str                     # "CONFORMS" | "DIVERGES"
    detail: str

@dataclass
class VerificationReport:
    service: str
    endpoints: list[EndpointVerification]
    mapping_conformance: list[MappingConformance]
    replay_result: ReplayResult | None = None  # Risk 17
    verdict: str                    # "PASS" | "FAIL" | "PASS (with notes)"
```

---

## 5. Phase 1: Foundation + Core Engine

### 5.1 `core/state.py` — ProjectState

```python
class ProjectState:
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.modernize_dir = self.project_path / ".modernize"
        self.migration_file = self.modernize_dir / "migration.json"

    @property
    def is_initialized(self) -> bool: ...

    def init(self, source_path: str, source_adapters: list[str],
             target_stack: list[dict], provider: str,
             trust_level: str, model: str | None = None) -> None:
        """Create .modernize/ directory structure and migration.json.
        Directory structure:
            ast, semantics, docs, corrections, locked,
            architecture, services, recordings, audit, audit/entries,
            components, checkpoints, reports, .locks
        Also creates: config-inventory.json (empty), asset-inventory.json (empty)
        migration.json schema: see below."""
        ...

    def load(self) -> dict:
        """Load migration.json. Raises StateError if not initialized."""
        ...

    def save(self, state: dict) -> None:
        """Write migration.json atomically (atomic_write_json)."""
        ...

    def update_step(self, step: str, status: str, **extra) -> None:
        """Update a pipeline step's status."""
        ...

    def get_step_status(self, step: str) -> str: ...

    def write_artifact(self, subdir: str, filename: str, data, as_json: bool = True) -> Path:
        """Write artifact with schema version stamp. Uses atomic_write_json."""
        ...

    def read_artifact(self, subdir: str, filename: str, as_json: bool = True) -> dict | str | None:
        """Read an artifact. Check schema version (Risk 20). Returns None if not found."""
        ...

    def list_artifacts(self, subdir: str, suffix: str = ".json") -> list[str]: ...
```

**migration.json schema:**

```json
{
  "schemaVersion": "2.1",
  "generatedBy": "modernize@0.1.0",
  "projectName": "coldfusion-app",
  "sourcePath": "./coldfusion-app",
  "sourceAdapters": ["coldfusion", "python"],
  "targetStack": [
    {"adapter": "react", "role": "frontend"},
    {"adapter": "go", "role": "backend"}
  ],
  "provider": "claude",
  "model": "claude-sonnet-4-6",
  "trustLevel": "standard",
  "executionMode": "guided",
  "budget": {"maxTotal": null, "warnAt": null},
  "concurrency": {"maxParallel": 5, "rateLimit": null},
  "steps": {
    "parse": {"status": "pending"},
    "extract": {"status": "pending"},
    "document": {"status": "pending"},
    "review": {"status": "pending"},
    "lockSemantics": {"status": "pending"},
    "analyzeExisting": {"status": "pending"},
    "chooseTargetStack": {"status": "pending"},
    "designTarget": {"status": "pending"},
    "reviewArchitect": {"status": "pending"},
    "lockArchitecture": {"status": "pending"},
    "generate": {"status": "pending"},
    "verify": {"status": "pending"}
  },
  "serviceGroups": [],
  "createdAt": "2026-04-01T10:00:00Z"
}
```

### 5.2 `core/encoding.py` — Encoding Detection (Risk 23)

```python
from charset_normalizer import from_bytes

class EncodingDetector:
    def detect_and_read(self, file_path: Path) -> tuple[str, str, float]:
        """Detect encoding and return (content_as_utf8, detected_encoding, confidence).

        Flow:
        1. Read file as bytes
        2. Check for BOM (UTF-8 BOM, UTF-16 LE/BE)
        3. Use charset_normalizer.from_bytes() for heuristic detection
        4. If confidence < 0.8, log warning
        5. Decode with detected encoding, return as UTF-8 string

        Returns: (utf8_content, original_encoding, detection_confidence)
        Raises: EncodingError if file is binary or detection fails completely.
        """
        raw = file_path.read_bytes()

        # Check for BOM
        if raw.startswith(b'\xef\xbb\xbf'):
            return raw[3:].decode('utf-8'), 'utf-8-bom', 1.0

        result = from_bytes(raw).best()
        if result is None:
            raise EncodingError(f"Cannot detect encoding for {file_path}")

        encoding = result.encoding
        confidence = result.encoding.confidence if hasattr(result, 'confidence') else 0.9
        content = str(result)

        return content, encoding, confidence

    def is_binary(self, file_path: Path) -> bool:
        """Check if file is binary (images, compiled objects).
        Reads first 8KB, checks for null bytes."""
        chunk = file_path.read_bytes()[:8192]
        return b'\x00' in chunk
```

### 5.3 `core/file_lock.py` — Advisory File Locking (Risk 28)

```python
import os
import json
import time

class FileLock:
    """Advisory file locking for concurrent pipeline access."""

    def __init__(self, locks_dir: Path):
        self.locks_dir = locks_dir
        self.locks_dir.mkdir(parents=True, exist_ok=True)

    def acquire(self, step: str, scope: str = "global", holder: str = "") -> PipelineLock:
        """Acquire a pipeline lock. Raises ConcurrencyError if already held.

        Lock file: .modernize/.locks/<step>-<scope>.lock
        Content: JSON with holder, PID, timestamp

        Flow:
        1. Build lock file path
        2. Check if lock file exists
        3. If exists: check if PID is still running (os.kill(pid, 0))
           - If running: raise ConcurrencyError
           - If not running: stale lock — remove it, log warning
        4. Write lock file with current PID
        5. Return PipelineLock
        """
        lock_file = self.locks_dir / f"{step}-{scope}.lock"

        if lock_file.exists():
            existing = json.loads(lock_file.read_text())
            if self._is_process_running(existing["pid"]):
                raise ConcurrencyError(existing["holder"], str(lock_file))
            else:
                # Stale lock
                lock_file.unlink()

        lock = PipelineLock(
            step=step, scope=scope, holder=holder or os.getenv("USER", "unknown"),
            pid=os.getpid(), acquired_at=datetime.utcnow().isoformat() + "Z",
            lock_file=str(lock_file)
        )
        atomic_write_json(lock_file, lock.to_dict())
        return lock

    def release(self, step: str, scope: str = "global") -> None:
        """Release a pipeline lock."""
        lock_file = self.locks_dir / f"{step}-{scope}.lock"
        if lock_file.exists():
            lock_file.unlink()

    def check_stale(self) -> list[PipelineLock]:
        """Find all stale locks (PID not running)."""
        stale = []
        for f in self.locks_dir.glob("*.lock"):
            data = json.loads(f.read_text())
            if not self._is_process_running(data["pid"]):
                stale.append(PipelineLock.from_dict(data))
        return stale

    def _is_process_running(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
```

### 5.4 `core/checkpoint.py` — Pipeline State Recovery (Risk 15)

```python
class CheckpointManager:
    def __init__(self, checkpoints_dir: Path):
        self.checkpoints_dir = checkpoints_dir
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    def create(self, step: str, all_modules: list[str]) -> Checkpoint:
        """Create a new checkpoint for a pipeline step."""
        cp = Checkpoint(
            step=step,
            started_at=datetime.utcnow().isoformat() + "Z",
            status="in-progress",
            completed=[],
            failed=[],
            remaining=list(all_modules),
        )
        self._save(cp)
        return cp

    def update(self, step: str, module: str, success: bool, error: str = "") -> None:
        """Mark a module as completed or failed in the checkpoint."""
        cp = self.load(step)
        if cp is None:
            return
        cp.current_module = ""
        if success:
            cp.completed.append(module)
        else:
            cp.failed.append({"module": module, "error": error})
        if module in cp.remaining:
            cp.remaining.remove(module)
        self._save(cp)

    def set_current(self, step: str, module: str) -> None:
        """Set the currently-processing module (for crash recovery)."""
        cp = self.load(step)
        if cp:
            cp.current_module = module
            self._save(cp)

    def complete(self, step: str) -> None:
        """Mark checkpoint as completed."""
        cp = self.load(step)
        if cp:
            cp.status = "completed"
            cp.remaining = []
            cp.current_module = ""
            self._save(cp)

    def load(self, step: str) -> Checkpoint | None:
        """Load checkpoint for a step. Returns None if no checkpoint exists."""
        path = self.checkpoints_dir / f"{step}.json"
        if not path.exists():
            return None
        return Checkpoint.from_dict(json.loads(path.read_text()))

    def get_resumable(self, step: str) -> list[str]:
        """Get list of modules to process (remaining + current_module if interrupted).
        The current_module is re-processed from scratch (partial output discarded)."""
        cp = self.load(step)
        if cp is None:
            return []
        modules = list(cp.remaining)
        if cp.current_module and cp.current_module not in modules:
            modules.insert(0, cp.current_module)
        return modules

    def _save(self, cp: Checkpoint) -> None:
        atomic_write_json(self.checkpoints_dir / f"{cp.step}.json", cp.to_dict())
```

### 5.5 `core/audit.py` — Audit Logging with Hash Chain (Risk 26)

```python
import hashlib

class AuditLogger:
    def __init__(self, audit_dir: Path):
        self.audit_dir = audit_dir
        self.entries_dir = audit_dir / "entries"
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self._sequence = self._get_next_sequence()

    def _get_next_sequence(self) -> int:
        existing = sorted(self.entries_dir.glob("*.json"))
        if not existing:
            return 1
        last = json.loads(existing[-1].read_text())
        return last["sequence"] + 1

    def _get_previous_hash(self) -> str:
        if self._sequence == 1:
            return "sha256:" + "0" * 64
        prev_file = self.entries_dir / f"{self._sequence - 1:06d}.json"
        if prev_file.exists():
            prev = json.loads(prev_file.read_text())
            return prev["entryHash"]
        return "sha256:" + "0" * 64

    def _compute_hash(self, entry_dict: dict) -> str:
        """Compute SHA-256 of entry (excluding entryHash field itself)."""
        hashable = {k: v for k, v in entry_dict.items() if k != "entryHash"}
        content = json.dumps(hashable, sort_keys=True, default=str)
        return "sha256:" + hashlib.sha256(content.encode()).hexdigest()

    def log(self, action: str, module: str, actor: str, details: dict) -> Path:
        """Write an audit entry with hash chain.

        Returns path to the audit entry file.
        """
        entry = AuditEntry(
            sequence=self._sequence,
            timestamp=datetime.utcnow().isoformat() + "Z",
            action=action,
            module=module,
            actor=actor,
            details=details,
            previous_hash=self._get_previous_hash(),
        )
        entry_dict = entry.to_dict()
        entry_dict["entryHash"] = self._compute_hash(entry_dict)

        path = self.entries_dir / f"{self._sequence:06d}.json"
        atomic_write_json(path, entry_dict)
        self._sequence += 1
        return path

    def log_ai_call(self, stage: str, module: str, provider: str, model: str,
                    input_tokens: int, output_tokens: int, duration_ms: int,
                    redacted_fields: list[str] = None) -> Path:
        """Convenience: log an AI API call."""
        return self.log(
            action="ai_call",
            module=module,
            actor=f"ai:{model}",
            details={
                "stage": stage, "provider": provider, "model": model,
                "inputTokens": input_tokens, "outputTokens": output_tokens,
                "durationMs": duration_ms, "redactedFields": redacted_fields or [],
            }
        )

    def verify_chain(self) -> tuple[bool, int]:
        """Verify the hash chain integrity (Risk 26).
        Returns (is_intact, break_point).
        break_point is -1 if intact, or the sequence number where the chain breaks."""
        entries = sorted(self.entries_dir.glob("*.json"))
        prev_hash = "sha256:" + "0" * 64

        for entry_file in entries:
            entry = json.loads(entry_file.read_text())
            # Check previous_hash matches
            if entry["previousHash"] != prev_hash:
                return False, entry["sequence"]
            # Recompute hash
            expected_hash = self._compute_hash(entry)
            if entry["entryHash"] != expected_hash:
                return False, entry["sequence"]
            prev_hash = entry["entryHash"]

        return True, -1

    def summarize(self) -> dict:
        """Return summary: total calls, tokens, cost estimate, per-stage breakdown."""
        ...
```

### 5.6 `core/cost.py` — Cost Estimation & Budget (Risk 16)

```python
# Pricing per 1M tokens (approximate, configurable)
DEFAULT_PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
}

class CostTracker:
    def __init__(self, audit_dir: Path, config: dict):
        self.audit_dir = audit_dir
        self.cost_file = audit_dir / "cost-summary.json"
        self.budget_max = config.get("budget", {}).get("maxTotal")
        self.budget_warn = config.get("budget", {}).get("warnAt")
        self.model = config.get("model", "claude-sonnet-4-6")

    def record_call(self, input_tokens: int, output_tokens: int, model: str = "") -> float:
        """Record a call's cost. Returns the call cost.
        Raises ModernizeError if budget exceeded."""
        model = model or self.model
        pricing = DEFAULT_PRICING.get(model, {"input": 5.0, "output": 15.0})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        summary = self._load_summary()
        summary["totalCost"] = summary.get("totalCost", 0) + cost
        summary["totalCalls"] = summary.get("totalCalls", 0) + 1
        summary["totalInputTokens"] = summary.get("totalInputTokens", 0) + input_tokens
        summary["totalOutputTokens"] = summary.get("totalOutputTokens", 0) + output_tokens

        # Per-stage tracking
        # ... (update per-stage costs)

        atomic_write_json(self.cost_file, summary)

        if self.budget_max and summary["totalCost"] > self.budget_max:
            raise ModernizeError(f"Budget exceeded: ${summary['totalCost']:.2f} > ${self.budget_max:.2f}")
        if self.budget_warn and summary["totalCost"] > self.budget_warn:
            from core import console
            console.print(f"[yellow]Warning: Budget at ${summary['totalCost']:.2f} / ${self.budget_max or 'unlimited'}[/]")

        return cost

    def estimate_step(self, step: str, module_count: int, avg_tokens_per_call: int = 2000) -> dict:
        """Dry-run cost estimation for --dry-run flag.
        Returns {"calls": N, "estimatedCost": X, "estimatedTime": "..."}"""
        pricing = DEFAULT_PRICING.get(self.model, {"input": 5.0, "output": 15.0})
        calls = module_count  # 1 call per module (rough estimate)
        input_cost = (calls * avg_tokens_per_call * pricing["input"]) / 1_000_000
        output_cost = (calls * (avg_tokens_per_call // 2) * pricing["output"]) / 1_000_000
        return {
            "calls": calls,
            "estimatedCost": round(input_cost + output_cost, 2),
            "estimatedInputCost": round(input_cost, 2),
            "estimatedOutputCost": round(output_cost, 2),
        }

    def _load_summary(self) -> dict:
        if self.cost_file.exists():
            return json.loads(self.cost_file.read_text())
        return {}
```

### 5.7 `core/confidence.py` — Confidence Scoring (Risk 5)

```python
class ConfidenceScorer:
    """Compute confidence from observable signals, not raw AI confidence."""

    def score_function(self, semantic_func: SemanticFunction, ast_func: ASTFunction,
                       ai_confidence: int = 90) -> int:
        """Compute calibrated confidence for a semantic function.

        Rules:
        - Fully deterministic extraction (source="deterministic") → 100
        - AI-assisted with strong AST evidence → max(ai_confidence, 85)
        - Purely AI-inferred (no AST evidence) → min(ai_confidence, 80)
        - Idempotency check failed (if available) → cap at 60
        """
        if semantic_func.business_rule.source == "deterministic":
            return 100
        if semantic_func.business_rule.source == "human":
            return 100

        # AI-assisted: check for AST evidence
        has_ast_evidence = (
            len(ast_func.queries) > 0 or
            len(ast_func.scope_writes) > 0 or
            len(ast_func.conditionals) > 0
        )

        if has_ast_evidence:
            return max(ai_confidence, 85)
        else:
            return min(ai_confidence, 80)

    def score_module(self, module: SemanticModule) -> int:
        """Compute overall module confidence (0-100).
        Average of function confidences, weighted by complexity."""
        if not module.functions:
            return 100
        total = sum(f.business_rule.confidence for f in module.functions)
        return round(total / len(module.functions))
```

### 5.8 `core/schema_version.py` — Schema Versioning (Risk 20)

```python
SCHEMA_VERSION = "2.1"
CLI_VERSION = "0.1.0"

# Migration registry: (from_version, to_version) → transform function
MIGRATIONS: dict[tuple[str, str], callable] = {}

def register_migration(from_v: str, to_v: str):
    """Decorator to register a schema migration function."""
    def decorator(func):
        MIGRATIONS[(from_v, to_v)] = func
        return func
    return decorator

@register_migration("2.0", "2.1")
def migrate_2_0_to_2_1(data: dict) -> dict:
    """Add parseStatus field to AST artifacts, restructure controlFlow."""
    if "parseStatus" not in data:
        data["parseStatus"] = "complete"
    if "unparsedBlocks" not in data:
        data["unparsedBlocks"] = []
    if "adapterVersion" not in data:
        data["adapterVersion"] = ""
    data["schemaVersion"] = "2.1"
    return data

def check_version(data: dict) -> str | None:
    """Check artifact schema version. Returns None if current, or the found version."""
    found = data.get("schemaVersion", "1.0")
    if found == SCHEMA_VERSION:
        return None
    return found

def migrate_artifact(data: dict) -> dict:
    """Migrate artifact to current schema version. Applies chain of migrations."""
    current = data.get("schemaVersion", "1.0")
    while current != SCHEMA_VERSION:
        # Find migration path
        migration = MIGRATIONS.get((current, SCHEMA_VERSION))
        if migration:
            data = migration(data)
            current = SCHEMA_VERSION
        else:
            raise SchemaVersionError(SCHEMA_VERSION, current)
    return data

def stamp(data: dict) -> dict:
    """Stamp artifact with current schema + CLI version."""
    data["schemaVersion"] = SCHEMA_VERSION
    data["generatedBy"] = f"modernize@{CLI_VERSION}"
    return data
```

### 5.9 `core/sanitizer.py` — Data Redaction

Same as original IMPLEMENTATION-PLAN.md Section 5.2. No changes needed — sanitizer works on AST node values and semantic model fields.

### 5.10 `core/chunker.py` — AST-Level Chunking

Same as original IMPLEMENTATION-PLAN.md Section 5.3. Includes Risk 4 mitigation: prior chunk results passed as context.

### 5.11 `core/context_assembler.py` — Context Packets

Same as original IMPLEMENTATION-PLAN.md Section 5.4.

### 5.12 `core/aggregator.py` — Merge Results

Same as original IMPLEMENTATION-PLAN.md Section 5.5. Includes Risk 4 deduplication pass.

### 5.13 `providers/` — AI Provider Adapters

Same as original IMPLEMENTATION-PLAN.md Sections 5.7–5.11 (base.py, claude.py, openai_provider.py, gemini.py, factory).

### 5.14 `agents/` — Agent System

Same as original IMPLEMENTATION-PLAN.md Sections 5.12–5.14 (loader.py, resolver.py, registry.py).

### 5.15 `modernize.py` — CLI Entry Point

Use Click. Extended command set (full reference in Section 14).

```python
@click.group()
@click.option("--project-dir", default=".", help="Project directory")
@click.pass_context
def cli(ctx, project_dir):
    """modernize — AI-Powered Legacy App Modernization Framework (v2)"""
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = project_dir

@cli.command()
@click.argument("source_path")
@click.option("--source-adapters", default="coldfusion", help="Comma-separated source adapters")
@click.option("--target-stack", required=True)
@click.option("--provider", default="claude")
@click.option("--model", default=None)
@click.option("--trust-level", default="standard", type=click.Choice(["strict", "standard", "trust"]))
@click.option("--execution-mode", default="guided", type=click.Choice(["guided", "supervised", "auto"]))
@click.pass_context
def init(ctx, source_path, source_adapters, target_stack, provider, model, trust_level, execution_mode):
    """Initialize modernization project."""
    adapters = [a.strip() for a in source_adapters.split(",")]
    # ... create ProjectState and init
```

---

## 6. Phase 2: Parser + Extractor + ColdFusion Adapter

### 6.1 `adapters/source/base.py` — Source Adapter Interface (Updated)

```python
class SourceAdapter(ABC):
    @abstractmethod
    def detect(self, files: list[str]) -> bool: ...

    @abstractmethod
    def parse_to_ast(self, file_path: str, content: str | None = None) -> ASTComponent:
        """Parse a source file into semantic AST.
        If content is provided, use it (already encoding-normalized).
        Otherwise read the file directly."""
        ...

    @abstractmethod
    def classify_ast_node(self, node: ASTFunction) -> str: ...

    @abstractmethod
    def get_agent_definitions_dir(self) -> str: ...

    @abstractmethod
    def get_conventions(self) -> str: ...

    @abstractmethod
    def get_supported_extensions(self) -> list[str]: ...

    @abstractmethod
    def get_config_patterns(self) -> list[dict]:
        """Risk 18: Return config file patterns this adapter knows about.
        Format: [{"glob": "Application.cfc", "parser": "cfml_config"}, ...]"""
        ...

    @abstractmethod
    def get_locale_sensitive_functions(self) -> list[str]:
        """Risk 24: Return list of locale-sensitive function names.
        E.g., ["LSDateFormat", "LSNumberFormat", "LSCurrencyFormat", "LSParseCurrency"]"""
        ...

    def get_adapter_version(self) -> str:
        """Risk 22: Return adapter version hash.
        Format: '<name>@<semver>+sha256:<hash_of_adapter_source>'"""
        import hashlib
        adapter_dir = Path(__file__).parent
        source_hash = hashlib.sha256()
        for f in sorted(adapter_dir.rglob("*.py")):
            source_hash.update(f.read_bytes())
        return f"{self.__class__.__name__}@{self.VERSION}+sha256:{source_hash.hexdigest()[:12]}"
```

### 6.2 `adapters/source/coldfusion/config_parser.py` — Config Capture (Risk 18)

```python
class ColdFusionConfigParser:
    """Parse Application.cfc, web.xml, .properties files for config inventory."""

    def parse_application_cfc(self, content: str, file_path: str) -> dict:
        """Extract settings from Application.cfc.

        Look for:
        - this.datasource = "..." → datasource name
        - this.sessionmanagement = true/false
        - this.sessiontimeout = createTimeSpan(...)
        - this.setClientCookies = true/false
        - setLocale("en_US") → locale (Risk 24)
        - setTimeZone("America/New_York") → timezone (Risk 24)
        - this.customTagPaths = [...]
        - this.mappings = {...}

        Returns dict matching ConfigInventory fields.
        """
        config = {}

        # Datasource
        dsn_match = re.search(r'this\.datasource\s*=\s*["\'](\w+)["\']', content, re.IGNORECASE)
        if dsn_match:
            config["datasources"] = [{"name": dsn_match.group(1), "source": f"{file_path}:{self._line_num(content, dsn_match.start())}"}]

        # Session config
        session_timeout = re.search(r'this\.sessiontimeout\s*=\s*createTimeSpan\(([^)]+)\)', content, re.IGNORECASE)
        if session_timeout:
            config["session"] = {"timeout": session_timeout.group(1), "source": file_path}

        # Locale (Risk 24)
        locale_match = re.search(r'setLocale\s*\(\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
        if locale_match:
            config["locale"] = locale_match.group(1)

        # Timezone (Risk 24)
        tz_match = re.search(r'setTimeZone\s*\(\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
        if tz_match:
            config["timezone"] = tz_match.group(1)

        return config

    def parse_properties(self, content: str, file_path: str) -> list[dict]:
        """Parse Java .properties files → list of feature flags / custom settings."""
        settings = []
        for i, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                settings.append({"key": key.strip(), "value": value.strip(), "source": f"{file_path}:{i}"})
        return settings
```

### 6.3 ColdFusion Parser

Same as original IMPLEMENTATION-PLAN.md Section 6.2, with these additions:

**Additions to `ColdFusionParser`:**

```python
class ColdFusionParser:
    # ... all existing regex patterns from original plan ...

    # Risk 24: locale-sensitive functions
    LOCALE_FUNCTIONS = {
        "lsdateformat", "lsnumberformat", "lscurrencyformat",
        "lsparsecurrency", "lsparsenumber", "lsparsedate",
        "lseuroformat", "lstimeformat", "lsiscurrency",
        "lsisnumeric", "lsisdate"
    }

    def parse_file(self, file_path: str, content: str | None = None) -> ASTComponent:
        """Main entry point.
        If content is None, read the file (encoding detection happens in pipeline/parser.py).
        """
        if content is None:
            content = Path(file_path).read_text(encoding="utf-8")
        filename = Path(file_path).name

        try:
            if filename.endswith(".cfc"):
                ast = self._parse_component(content, filename)
            else:
                ast = self._parse_template(content, filename)
            ast.parse_status = "complete"
            ast.coverage_percent = 100.0
        except Exception as e:
            # Risk 21: graceful degradation
            ast = self._create_failed_ast(filename, str(e))

        return ast

    def _create_failed_ast(self, filename: str, error: str) -> ASTComponent:
        """Risk 21: Create a failed-parse AST placeholder."""
        name = Path(filename).stem
        return ASTComponent(
            name=name,
            file=filename,
            type="component" if filename.endswith(".cfc") else "template",
            parse_status="failed",
            unparsed_blocks=[UnparsedBlock(
                start_line=1, end_line=0,
                raw_text="[entire file]",
                reason=f"Parse failed: {error}"
            )],
            coverage_percent=0.0,
        )

    def _detect_locale_sensitivity(self, body: str) -> tuple[bool, list[str]]:
        """Risk 24: Check if function body uses locale-sensitive CF functions."""
        found = []
        for call_match in self.RE_FUNCTION_CALL.finditer(body):
            func_name = call_match.group(1).lower()
            if func_name in self.LOCALE_FUNCTIONS:
                found.append(call_match.group(1))  # Original case
        return bool(found), found
```

### 6.4 SQL Extractor, ColdFusion Adapter, Agent YAML Files

Same as original IMPLEMENTATION-PLAN.md Sections 6.3–6.5.

### 6.5 `pipeline/parser.py` — Step 1: Parse to AST (Updated)

```python
def run_parse(state: ProjectState, incremental: bool = True,
              force: bool = False, coverage_report: bool = False) -> None:
    """Step 1 — Parse legacy source to AST.

    Flow:
    1. Verify project is initialized
    2. Acquire pipeline lock (Risk 28): FileLock.acquire("parse", "global")
    3. Load migration.json to get source path + source adapters
    4. Create/load checkpoint (Risk 15)
    5. For each source adapter:
       a. Find all source files matching adapter extensions
       b. For each file:
          i.   Risk 23: Detect encoding, normalize to UTF-8
          ii.  Risk 11: Check file hash — skip if unchanged AND adapter version matches (unless --force)
          iii. Risk 22: Check adapter version — re-parse if adapter changed
          iv.  Call adapter.parse_to_ast(file_path, content)
          v.   Stamp adapter version + source hash + encoding metadata on AST
          vi.  Write to .modernize/ast/<filename>.ast.json
          vii. Update checkpoint
    6. Risk 18: Run config capture
       a. For each adapter, get config patterns
       b. Find matching config files, parse them
       c. Write .modernize/config-inventory.json
    7. Risk 25: Run static asset inventory
       a. Scan source directory for non-source files
       b. Cross-reference with AST (cfinclude, script src, img src, etc.)
       c. Classify actions (copy/replace/migrate/review)
       d. Write .modernize/asset-inventory.json
    8. Risk 21: If --coverage-report, print grammar coverage stats
    9. Release pipeline lock
    10. Display progress with Rich
    11. Complete checkpoint

    Error handling:
    - File parse failure → log, mark as failed in checkpoint, continue
    - Encoding detection failure → log warning, try UTF-8, mark partial if fails
    """
    file_lock = FileLock(state.modernize_dir / ".locks")
    lock = file_lock.acquire("parse", "global")

    try:
        checkpoint_mgr = CheckpointManager(state.modernize_dir / "checkpoints")
        # ... implementation ...
    finally:
        file_lock.release("parse", "global")

def _scan_static_assets(source_path: Path, ast_components: list[ASTComponent]) -> AssetInventory:
    """Risk 25: Inventory non-code files and classify them.

    Asset type detection by extension:
    - .png, .jpg, .gif, .svg, .ico → "image"
    - .css → "css"
    - .js (in lib/ or vendor/) → "javascript-library"
    - .html (not .cfm) → "email-template" (if referenced by cfmail) or "other"
    - .pdf, .xls, .xlsx, .doc → "document-template"
    - .woff, .ttf, .eot → "font"

    Action classification:
    - Images, fonts, PDFs → "copy"
    - jQuery, legacy JS libraries → "replace" (React eliminates them)
    - HTML templates with CF expressions → "migrate"
    - Everything else → "review"
    """
    ...

def _capture_config(state: ProjectState, adapters: list[SourceAdapter],
                    source_path: Path) -> ConfigInventory:
    """Risk 18: Capture config files into config-inventory.json."""
    inventory = ConfigInventory()
    for adapter in adapters:
        for pattern in adapter.get_config_patterns():
            for config_file in source_path.glob(pattern["glob"]):
                content = config_file.read_text(errors="replace")
                # Parse based on parser type
                if pattern["parser"] == "cfml_config":
                    config_parser = ColdFusionConfigParser()
                    result = config_parser.parse_application_cfc(content, str(config_file))
                    # Merge into inventory
                    ...
    return inventory
```

### 6.6 `pipeline/extractor.py` — Step 2 (Updated)

Same as original IMPLEMENTATION-PLAN.md Section 6.7, with these additions:

```python
def run_extract(state: ProjectState, dry_run: bool = False,
                retry_failed: bool = False) -> None:
    """Step 2 — Extract semantics from AST.

    Additions over original plan:
    - Risk 15: Checkpoint/resume support
    - Risk 16: --dry-run cost estimation
    - Risk 5: Confidence scoring via ConfidenceScorer
    - Risk 1: Cross-module consistency check after all extractions
    - Risk 24: Flag locale-sensitive functions
    - Risk 28: File locking

    If --dry-run: estimate cost and print, don't execute.
    If --retry-failed: only re-extract modules marked as failed in checkpoint.
    """
    if dry_run:
        # Count modules, estimate cost
        ast_files = state.list_artifacts("ast", ".json")
        cost_tracker = CostTracker(state.modernize_dir / "audit", state.load())
        estimate = cost_tracker.estimate_step("extract", len(ast_files))
        console.print(f"Estimated: {estimate['calls']} API calls, ${estimate['estimatedCost']:.2f}")
        return

    # ... normal extraction with checkpoint support ...

    # After all extractions complete:
    _run_consistency_check(state)  # Risk 1

def _run_consistency_check(state: ProjectState) -> None:
    """Risk 1: Cross-module consistency check.

    For every module's `calls` list:
    1. Find the target module's semantic model
    2. Compare caller's description of the function with callee's actual signature
    3. Flag mismatches in consistency-report.json

    This is deterministic — no AI needed.
    """
    all_modules = {}
    for fname in state.list_artifacts("semantics", ".semantic.json"):
        module = SemanticModule.from_dict(state.read_artifact("semantics", fname))
        all_modules[module.module] = module

    mismatches = []
    for name, module in all_modules.items():
        for func in module.functions:
            for call_target in func.calls:
                # Parse "ModuleName.functionName" or just "functionName"
                parts = call_target.split(".")
                if len(parts) == 2:
                    target_module_name, target_func_name = parts
                    target_module = all_modules.get(target_module_name)
                    if target_module:
                        target_func = next((f for f in target_module.functions if f.name == target_func_name), None)
                        if target_func:
                            # Compare signatures
                            caller_args = len(func.signature.get("inputs", []))
                            callee_args = len(target_func.signature.get("inputs", []))
                            if caller_args != callee_args:
                                mismatches.append({
                                    "caller": f"{name}.{func.name}",
                                    "callee": f"{target_module_name}.{target_func_name}",
                                    "issue": f"Argument count mismatch: caller passes {caller_args}, callee expects {callee_args}",
                                })

    state.write_artifact("semantics", "consistency-report.json", {"mismatches": mismatches})
```

### 6.7 `pipeline/reviewer.py` — Step 4 (Updated)

Same as original IMPLEMENTATION-PLAN.md Section 6.9, with Risk 19 conflict resolution:

```python
def run_correct(state: ProjectState, target: str, field: str, value: str,
                reviewer: str = "") -> None:
    """Apply a correction with conflict detection (Risk 19).

    Flow:
    1. Parse target: "ModuleName.functionName"
    2. Load existing corrections for this module
    3. Check if this field was already corrected by someone else
       - If yes: show conflict, ask for resolution (keep/replace/new)
       - If no: apply directly
    4. Write to .modernize/corrections/<module>.corrections.json
    5. Also update .modernize/semantics/<module>.semantic.json
    6. Risk 2: Run propagateImpact() — flag dependent modules as "needs-re-review"
    """
    module_name, func_name = target.split(".", 1) if "." in target else (target, "")

    # Load existing corrections
    corrections_file = f"{module_name}.corrections.json"
    existing = state.read_artifact("corrections", corrections_file) or {"corrections": [], "conflicts": []}

    # Check for conflicts (Risk 19)
    for corr in existing["corrections"]:
        if corr["field"] == field and corr.get("by") != reviewer:
            # Conflict detected!
            console.print(f"[yellow]CONFLICT: Field '{field}' already corrected by {corr['by']}[/]")
            console.print(f"  Their value: {corr['corrected']}")
            console.print(f"  Your value: {value}")
            choice = click.prompt("Choose: (k)eep theirs, (r)eplace with yours, (n)ew value", type=str)

            conflict_record = CorrectionConflict(
                field=field,
                reviewer_a={"value": corr["corrected"], "by": corr["by"]},
                reviewer_b={"value": value, "by": reviewer},
            )

            if choice == "k":
                conflict_record.resolution = corr["corrected"]
                conflict_record.resolved_by = reviewer
            elif choice == "r":
                conflict_record.resolution = value
                conflict_record.resolved_by = reviewer
                corr["corrected"] = value  # Update existing correction
            else:
                new_value = click.prompt("Enter new value")
                conflict_record.resolution = new_value
                conflict_record.resolved_by = reviewer
                corr["corrected"] = new_value

            existing["conflicts"] = existing.get("conflicts", [])
            existing["conflicts"].append(conflict_record.to_dict())
            state.write_artifact("corrections", corrections_file, existing)
            return

    # No conflict — apply normally
    correction = Correction(field=field, original="...", corrected=value, by=reviewer, at=datetime.utcnow().isoformat() + "Z")
    existing["corrections"].append(correction.to_dict())
    state.write_artifact("corrections", corrections_file, existing)

    # Also update semantic model
    _apply_correction_to_semantic(state, module_name, field, value)

    # Risk 2: propagate impact
    _propagate_impact(state, module_name, field)

def _propagate_impact(state: ProjectState, changed_module: str, changed_field: str) -> None:
    """Risk 2: When a correction touches a shared resource, flag dependent modules.

    Check cross-module.json for modules that depend on changed_module.
    If the correction touches a shared resource (table, state key, function signature),
    mark dependent modules as "needs-re-review".
    """
    cross_module = state.read_artifact("semantics", "cross-module.json")
    if not cross_module:
        return

    dep_graph = cross_module.get("dependencyGraph", {})
    for module_name, deps in dep_graph.items():
        if changed_module in deps.get("depends_on", []):
            # Flag as needs re-review
            semantic = state.read_artifact("semantics", f"{module_name}.semantic.json")
            if semantic and semantic.get("approved"):
                semantic["reviewStatus"] = "needs-re-review"
                state.write_artifact("semantics", f"{module_name}.semantic.json", semantic)
                console.print(f"[yellow]Flagged {module_name} for re-review (depends on {changed_module})[/]")
```

### 6.8 `pipeline/import_schema.py` — Database Catalog Import (Risk 13)

```python
def run_import_schema(state: ProjectState, connection_string: str,
                      include_procs: bool = False) -> None:
    """Import stored procedure signatures + bodies from database catalog.

    Uses SQLAlchemy to connect and query INFORMATION_SCHEMA / sys.sql_modules.

    Flow:
    1. Connect to database via connection_string
    2. Query for stored procedures:
       - SQL Server: sys.sql_modules + INFORMATION_SCHEMA.ROUTINES
       - MySQL: INFORMATION_SCHEMA.ROUTINES
       - Oracle: ALL_SOURCE
    3. For each procedure:
       a. Extract name, parameters, return type
       b. If --include-procs: extract body text
       c. Parse body with sqlglot to extract tables, operations, params
       d. Create SemanticModule with source="database-catalog"
       e. Write to .modernize/semantics/<proc_name>.semantic.json
    4. Update cross-module.json with procedure dependencies
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(connection_string)
    with engine.connect() as conn:
        # Detect database type
        dialect = engine.dialect.name

        if dialect == "mssql":
            procs = conn.execute(text("""
                SELECT r.ROUTINE_NAME, r.ROUTINE_TYPE, m.definition
                FROM INFORMATION_SCHEMA.ROUTINES r
                LEFT JOIN sys.sql_modules m ON OBJECT_ID(r.ROUTINE_NAME) = m.object_id
                WHERE r.ROUTINE_TYPE = 'PROCEDURE'
            """))
        # ... similar for mysql, oracle ...

        for proc in procs:
            semantic = _proc_to_semantic(proc, include_procs)
            state.write_artifact("semantics", f"{proc.ROUTINE_NAME}.semantic.json", semantic.to_dict())
```

---

## 7. Phase 3: Lock Manager + Architect Module

### 7.1 `pipeline/locker.py` — Lock Manager (Updated)

```python
def run_lock_semantics(state: ProjectState) -> None:
    """Step 5a — Lock semantic mappings (per-module granularity, Risk 3).

    Flow:
    1. Verify all modules are approved (or re-check: no "needs-re-review" status)
    2. For modules with "needs-re-review": block lock, list them
    3. For each approved module:
       a. Serialize semantic model (sorted keys)
       b. Compute SHA-256 checksum
       c. Record source_hash and ast_hash (Risk 11)
       d. Build LockedModule
    4. Build SemanticLock + LockManifest
    5. Write .modernize/locked/semantic-lock.json
    6. Write .modernize/locked/lock-manifest.json
    7. Audit log the lock event (Risk 26)
    """
    ...

def run_unlock_semantics(state: ProjectState, module_name: str | None = None) -> None:
    """Unlock semantic mappings. Risk 3: per-module unlock.

    If module_name given: unlock just that module.
    If None: unlock all. Requires --force if architecture is also locked.

    When unlocking a module:
    1. Remove its entry from semantic-lock.json
    2. Update lock-manifest (set status="partial")
    3. Risk 2: Flag dependent modules as "needs-re-review"
    """
    ...

def verify_lock_integrity(state: ProjectState) -> bool:
    """Verify locked files haven't been tampered with.
    Also checks source file hashes (Risk 11) — flags stale modules."""
    lock = state.read_artifact("locked", "semantic-lock.json")
    manifest = state.read_artifact("locked", "lock-manifest.json")

    for module_name, locked_module in lock["modules"].items():
        # Recompute checksum
        content = json.dumps(locked_module["semantics"], sort_keys=True)
        expected = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
        if expected != locked_module["checksum"]:
            return False

        # Risk 11: Check source file hash hasn't changed
        source_file = Path(state.load()["sourcePath"]) / locked_module["semantics"]["source"]
        if source_file.exists():
            current_hash = "sha256:" + hashlib.sha256(source_file.read_bytes()).hexdigest()
            if current_hash != locked_module.get("sourceHash", ""):
                locked_module["status"] = "stale"
                # Don't return False — just flag as stale

    return True
```

### 7.2 `pipeline/architect.py` — Architecture Module (Updated for 5b/5c/5d Split)

```python
def run_architect_existing(state: ProjectState) -> None:
    """Step 5b — Analyze existing architecture from locked semantics.

    Generates BEFORE target stack is chosen.

    AI tasks:
    1. Module inventory: complexity scores, roles
    2. Coupling map: which modules call each other, how tightly coupled
    3. Data flow diagram: which modules read/write which tables
    4. Shared state map: session/application scope across modules
    5. Natural service boundaries: where the codebase has clean seams

    Output: .modernize/architecture/existing-architecture.md
    This is a consulting deliverable — goes to client before target stack discussion.
    """
    # Verify semantics are locked
    if state.get_step_status("lockSemantics") != "completed":
        raise PipelineError("analyzeExisting", "Semantics not locked. Run 'modernize lock semantics' first.")

    lock = state.read_artifact("locked", "semantic-lock.json")
    provider = create_provider(state.load()["provider"])

    # AI call: analyze existing architecture
    prompt = f"""You are analyzing a legacy ColdFusion application's architecture.
Given the locked semantic model below, produce a comprehensive analysis of the existing architecture.

LOCKED SEMANTIC MODEL:
{json.dumps(lock["modules"], indent=2)}

CROSS-MODULE DEPENDENCIES:
{json.dumps(lock.get("crossModule", {}), indent=2)}

Produce a markdown document with these sections:
1. Module Inventory (table: name, complexity, role, tables owned)
2. Coupling Map (which modules are tightly coupled and why)
3. Data Flow (which modules read/write which tables)
4. Shared State Dependencies (session/application scope sharing)
5. Natural Service Boundaries (where the code could cleanly split)
6. Entanglements (where splitting will be difficult)
"""

    response = provider.send_prompt(
        "You are a software architect analyzing legacy application structure.",
        prompt,
        output_format="text"
    )

    state.write_artifact("architecture", "existing-architecture.md", response.content, as_json=False)
    state.update_step("analyzeExisting", "completed")

def run_config_target_stack(state: ProjectState, frontend: str, backend: str,
                           workers: str | None = None) -> None:
    """Step 5c — Choose target stack (human decision, no AI).

    Records the human decision in migration.json with attribution.
    """
    migration = state.load()
    migration["targetStack"] = {
        "frontend": frontend,
        "backend": backend,
        "workers": workers or backend,
        "chosenBy": os.getenv("USER", "unknown"),
        "chosenAt": datetime.utcnow().isoformat() + "Z",
    }
    state.save(migration)
    state.update_step("chooseTargetStack", "completed")
    console.print(f"[green]Target stack configured: {frontend} (frontend) + {backend} (backend)[/]")

def run_architect_target(state: ProjectState) -> None:
    """Step 5d — Design target architecture from locked semantics + target stack.

    Requires: semantics locked + existing architecture analyzed + target stack chosen.

    AI tasks:
    1. group_service_boundaries: Analyze dependencies → suggest service groups
    2. define_api_contracts: REST endpoints per service group
    3. route_components: Legacy functions → target components + stack layers
    4. map_data: Legacy state → modern equivalents (JWT, env vars)
    5. Risk 27: Generate URL mappings (legacy URLs → new endpoints)

    Output:
    - .modernize/architecture/target-architecture.md
    - .modernize/architecture/architecture-decisions.json
    """
    # Verify prerequisites
    for step in ["lockSemantics", "analyzeExisting", "chooseTargetStack"]:
        if state.get_step_status(step) != "completed":
            raise PipelineError("designTarget", f"Step '{step}' not completed.")

    lock = state.read_artifact("locked", "semantic-lock.json")
    existing_arch = state.read_artifact("architecture", "existing-architecture.md", as_json=False)
    migration = state.load()
    target_stack = migration["targetStack"]
    provider = create_provider(migration["provider"])

    # AI calls for service grouping, API contracts, component routing, data mapping
    # (Same AI prompts as original IMPLEMENTATION-PLAN.md Section 7.2)
    # ...

    # Risk 27: URL mapping generation
    url_mappings = _generate_url_mappings(lock, architecture_decisions, provider)
    architecture_decisions["urlMappings"] = [m.to_dict() for m in url_mappings]

    state.write_artifact("architecture", "architecture-decisions.json", architecture_decisions)
    state.write_artifact("architecture", "target-architecture.md", target_arch_md, as_json=False)
    state.update_step("designTarget", "completed")

def _generate_url_mappings(lock: dict, arch: dict, provider) -> list[URLMapping]:
    """Risk 27: Generate URL mappings from legacy routes to new endpoints.

    Sources of legacy URLs:
    - Application.cfc onRequestStart routing patterns
    - <form action="..."> targets in AST
    - <a href="..."> links in AST
    - <cflocation url="..."> redirects in AST

    For each legacy URL pattern, map to the corresponding new REST endpoint
    from the architecture decisions.
    """
    ...
```

---

## 8. Phase 4: Generator Module + React/Go Adapters

### 8.1 Target Adapter Interfaces

Same as original IMPLEMENTATION-PLAN.md Sections 8.1–8.3 (base.py, react/adapter.py, go/adapter.py).

### 8.2 `pipeline/generator.py` — Step 6 (Updated)

Same as original IMPLEMENTATION-PLAN.md Section 8.4, with these additions:

```python
def run_generate(state: ProjectState, service_name: str) -> None:
    """Step 6 — Generate code. Additions:

    - Risk 12: Track generation baseline hash per file
    - Risk 12: Detect human modifications, offer merge/overwrite/skip
    - Risk 25: Copy static assets for this service group
    - Risk 27: Generate proxy config with URL rewrite rules
    - Risk 24: Locale-aware generation (explicit locale params in target code)
    - Risk 28: File lock per service group (concurrent generation safe)
    """
    file_lock = FileLock(state.modernize_dir / ".locks")
    lock = file_lock.acquire("generate", service_name)

    try:
        # ... generation logic ...

        # Risk 12: Check for human modifications before overwriting
        manifest = _load_generation_manifest(state, service_name)
        if manifest:
            modified = _detect_human_edits(state, service_name, manifest)
            if modified:
                _handle_modified_files(modified)  # Prompt: overwrite/merge/skip

        # ... generate code ...

        # Risk 12: Save generation baseline
        _save_generation_manifest(state, service_name, generated_files)

        # Risk 25: Copy static assets
        _copy_static_assets(state, service_name)

        # Risk 27: Generate proxy config with URL rewrites
        _generate_proxy_config(state, service_name)

    finally:
        file_lock.release("generate", service_name)

def _save_generation_manifest(state: ProjectState, service: str, files: list[Path]) -> None:
    """Risk 12: Save generation baseline hashes."""
    manifest = {"service": service, "files": {}}
    for f in files:
        content_hash = "sha256:" + hashlib.sha256(f.read_bytes()).hexdigest()
        manifest["files"][str(f.relative_to(state.modernize_dir))] = {
            "baselineHash": content_hash,
            "currentHash": content_hash,
            "status": "generated",
        }
    state.write_artifact(f"services/{service}", "generation-manifest.json", manifest)

def _detect_human_edits(state: ProjectState, service: str, manifest: dict) -> list[dict]:
    """Risk 12: Detect files modified since last generation."""
    modified = []
    for filepath, meta in manifest["files"].items():
        full_path = state.modernize_dir / filepath
        if full_path.exists():
            current_hash = "sha256:" + hashlib.sha256(full_path.read_bytes()).hexdigest()
            if current_hash != meta["baselineHash"] and meta["status"] != "manually-maintained":
                modified.append({"path": filepath, "status": meta["status"]})
    return modified

def _generate_proxy_config(state: ProjectState, service_name: str) -> None:
    """Risk 27: Generate proxy routing + URL rewrite config."""
    arch = state.read_artifact("architecture", "architecture-decisions.json")
    url_mappings = arch.get("urlMappings", [])

    # Filter mappings for this service
    service_mappings = [m for m in url_mappings if _mapping_belongs_to_service(m, service_name, arch)]

    # Generate nginx config fragment
    nginx_config = _generate_nginx_config(service_name, service_mappings)
    state.write_artifact(f"services/{service_name}/proxy", "nginx.conf.fragment", nginx_config, as_json=False)

    # Generate HAProxy config fragment
    haproxy_config = _generate_haproxy_config(service_name, service_mappings)
    state.write_artifact(f"services/{service_name}/proxy", "haproxy.cfg.fragment", haproxy_config, as_json=False)

    # Generate routes.yaml
    routes = {"service": service_name, "mappings": service_mappings}
    state.write_artifact(f"services/{service_name}/proxy", "routes.yaml", routes)
```

### 8.3 Client Component Registry (Updated)

Updated to use YAML manifests per DESIGN-v2.md:

```python
def register_components(state: ProjectState, components_path: str) -> None:
    """Register client component library from YAML manifests.

    Scans the directory for component files, generates YAML manifests.

    Manifest format (.modernize/components/manifests/<Name>.yaml):
    name: DataTable
    package: "@acme/design-system"
    import: "import { DataTable } from '@acme/design-system'"
    role: data-display
    props:
      columns: {type: "ColumnDef[]", required: true}
      data: {type: "T[]", required: true}
    usage: |
      <DataTable columns={...} data={...} />
    """
    ...
```

---

## 9. Phase 5: Verifier Module

### 9.1 `pipeline/recorder.py` — HTTP Recording Proxy (Risk 17)

```python
def run_record(state: ProjectState, service_name: str,
               proxy_port: int = 8080, duration_minutes: int = 60,
               legacy_url: str = "http://localhost:8500") -> None:
    """Record HTTP request/response pairs from the legacy app.

    Starts a simple HTTP proxy that:
    1. Receives incoming requests
    2. Forwards to the legacy app
    3. Captures the request + response pair
    4. Sanitizes per trust level (redact PII, credentials)
    5. Writes to .modernize/recordings/<service>/recording-NNN.json

    Only records GET requests automatically.
    POST/PUT/DELETE are logged but marked "requires-manual-replay".

    Implementation: Use Python's http.server + urllib for the proxy.
    This is a lightweight capture proxy, not a full reverse proxy.
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.request

    recordings_dir = state.modernize_dir / "recordings" / service_name
    recordings_dir.mkdir(parents=True, exist_ok=True)
    sanitizer = Sanitizer()  # For redacting sensitive data

    counter = [0]

    class RecordingHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._proxy_and_record("GET")

        def do_POST(self):
            self._proxy_and_record("POST")

        def _proxy_and_record(self, method):
            # Forward to legacy app
            target_url = f"{legacy_url}{self.path}"
            req = urllib.request.Request(target_url, method=method)
            # Copy headers...

            try:
                with urllib.request.urlopen(req) as resp:
                    body = resp.read()
                    status = resp.status
            except Exception as e:
                body = str(e).encode()
                status = 502

            # Record the pair
            counter[0] += 1
            pair = RecordedPair(
                request={"method": method, "path": self.path, "headers": dict(self.headers)},
                legacy_response={"status": status, "body": body.decode(errors="replace")},
                recorded_at=datetime.utcnow().isoformat() + "Z",
            )
            # Sanitize
            sanitized_pair, _ = sanitizer.sanitize_dict(pair.to_dict())
            atomic_write_json(
                recordings_dir / f"recording-{counter[0]:04d}.json",
                sanitized_pair
            )

            # Forward response to caller
            self.send_response(status)
            self.end_headers()
            self.wfile.write(body)

    console.print(f"[green]Recording proxy started on port {proxy_port}[/]")
    console.print(f"Forwarding to {legacy_url}")
    console.print(f"Recording for {duration_minutes} minutes...")

    server = HTTPServer(("", proxy_port), RecordingHandler)
    server.timeout = duration_minutes * 60
    server.handle_request()  # Or use threading for continuous serving
```

### 9.2 `pipeline/verifier.py` — Step 7 (Updated)

Same as original IMPLEMENTATION-PLAN.md Section 9.1, with these additions:

```python
def run_verify(state: ProjectState, service_name: str,
               replay: bool = False) -> None:
    """Step 7 — Verify behavioral equivalence.

    Additions:
    - Risk 17: --replay flag triggers record-replay verification
    - Risk 6: Architecture conformance checking (deterministic)
    - Risk 7: Escalation paths in rejection workflow
    """
    # Part A: Locked Mapping Conformance (same as original)
    # Part B: Behavioral Analysis via AI (same as original)

    # Part C (new): Architecture Conformance (Risk 6)
    arch_conformance = _check_architecture_conformance(state, service_name)

    # Part D (new): Replay verification (Risk 17)
    replay_result = None
    if replay:
        replay_result = _run_replay(state, service_name)

    # Build report
    report = VerificationReport(
        service=service_name,
        endpoints=endpoint_results,
        mapping_conformance=mapping_results,
        replay_result=replay_result,
        verdict=_compute_verdict(endpoint_results, mapping_results, arch_conformance, replay_result),
    )

    state.write_artifact(f"recordings/{service_name}", "verification-report.json", report.to_dict())

def _check_architecture_conformance(state: ProjectState, service_name: str) -> list[dict]:
    """Risk 6: Deterministic check that generated code matches architecture lock.

    Checks:
    1. Each generated file belongs to the correct service group
    2. Generated API endpoints match locked contracts (method, path, request/response)
    3. Cross-service calls use the defined API, not direct function calls
    """
    arch = state.read_artifact("locked", "architecture-lock.json")
    # ... deterministic comparison ...
    return conformance_results

def _run_replay(state: ProjectState, service_name: str) -> ReplayResult:
    """Risk 17: Replay recorded requests against new service.

    Flow:
    1. Load recordings from .modernize/recordings/<service>/
    2. For each recording:
       a. Send same request to new service
       b. Capture response
       c. Diff: structural JSON comparison, type coercion normalization
       d. Classify: PASS / ACCEPTABLE_DRIFT / FAIL
    3. Write failures to .modernize/recordings/<service>/failures/
    4. Return ReplayResult summary
    """
    recordings_dir = state.modernize_dir / "recordings" / service_name
    recordings = sorted(recordings_dir.glob("recording-*.json"))

    passed = 0
    drift = 0
    failed = 0
    failures = []

    for rec_file in recordings:
        pair = RecordedPair.from_dict(json.loads(rec_file.read_text()))

        # Only auto-replay GET requests
        if pair.request["method"] != "GET":
            continue

        # Send to new service
        # ... (make HTTP request to new service URL)

        # Structural diff
        diff = _structural_diff(pair.legacy_response["body"], new_response_body)

        if diff["status"] == "PASS":
            passed += 1
        elif diff["status"] == "DRIFT":
            drift += 1
        else:
            failed += 1
            failures.append({"recording": rec_file.name, "diff": diff})

    return ReplayResult(
        total_requests=passed + drift + failed,
        passed=passed,
        acceptable_drift=drift,
        failed=failed,
        failures=failures,
    )

def run_reject_verify(state: ProjectState, service_name: str,
                      escalate: str | None = None) -> None:
    """Risk 7: Rejection with escalation paths.

    escalate options:
    - None: regenerate (Step 6 only)
    - "architecture": unlock architecture → re-design → re-lock → regenerate
    - "semantics": unlock semantics → re-review → re-lock → re-architect → regenerate
    """
    if escalate is None:
        # Just re-run generation
        state.update_step("generate", "pending")
        console.print(f"[yellow]Regeneration required for {service_name}. Run 'modernize generate {service_name}'[/]")
    elif escalate == "architecture":
        state.update_step("lockArchitecture", "pending")
        state.update_step("designTarget", "pending")
        console.print("[yellow]Architecture escalation. Steps reset: designTarget → lockArchitecture → generate[/]")
    elif escalate == "semantics":
        # Unlock everything back to semantics
        run_unlock_semantics(state)
        console.print("[yellow]Semantics escalation. Full pipeline reset from review step.[/]")
```

---

## 10. Phase 6: Polish + Auto Mode

### 10.1 `pipeline/runner.py` — Auto Mode

Same as original IMPLEMENTATION-PLAN.md Section 10.1, with Risk 14 calibration gate:

```python
def run_all(state: ProjectState, auto_approve: bool = True) -> None:
    """Risk 14: Auto mode with calibration gate.

    Auto mode is only available after a manual calibration run.
    Check: has at least one service group been processed manually?
    If not, warn and require --force-auto to bypass.

    Hard exclusions (never auto-approve):
    - Modules with any field below 85% confidence
    - Modules flagged by discovery gaps
    - Modules touching PII tables
    - Modules with external dependency stubs
    """
    migration = state.load()

    if auto_approve and migration.get("executionMode") == "auto":
        # Risk 14: Check calibration
        if not migration.get("calibrationComplete", False):
            console.print("[red]Auto mode requires calibration. Process at least one service group manually first.[/]")
            console.print("Or use: modernize run --all --force-auto")
            return

    # ... pipeline execution with hard exclusions check ...
```

### 10.2 `pipeline/reporter.py` — Pipeline Observability

```python
def run_status(state: ProjectState, show_stale: bool = False) -> None:
    """Show pipeline progress table.

    Reads: migration.json, checkpoints, lock manifests, cost-summary.json.
    Output: Rich table matching the mockup in DESIGN-v2.md Pipeline Observability section.

    If --stale: also show locked modules whose source files changed (Risk 11).
    """
    migration = state.load()

    # Build status table
    table = Table(title=f"Project: {migration['projectName']}")
    table.add_column("Stage")
    table.add_column("Done")
    table.add_column("Review")
    table.add_column("Failed")
    table.add_column("Stale")
    table.add_column("Left")

    # ... populate from migration.json steps + checkpoint data ...

    # Risk 28: Check for stale locks
    file_lock = FileLock(state.modernize_dir / ".locks")
    stale_locks = file_lock.check_stale()
    if stale_locks:
        console.print(f"[yellow]WARNING: {len(stale_locks)} stale lock(s) detected. Run 'modernize unlock-pipeline' to clean up.[/]")

    # Cost summary
    cost_file = state.modernize_dir / "audit" / "cost-summary.json"
    if cost_file.exists():
        cost = json.loads(cost_file.read_text())
        console.print(f"Cost so far: ${cost.get('totalCost', 0):.2f} ({cost.get('totalCalls', 0)} API calls)")

def run_report(state: ProjectState, weekly: bool = False) -> None:
    """Generate markdown progress report.

    Output: .modernize/reports/week-YYYY-MM-DD.md
    Contents: modules processed, reviewed, cost, blockers, forecast.
    """
    ...
```

### 10.3 Schema Migration CLI (Risk 20)

```python
def run_migrate(state: ProjectState, dry_run: bool = False) -> None:
    """Migrate .modernize/ artifacts to current schema version.

    Flow:
    1. Scan all JSON artifacts in .modernize/
    2. Check schemaVersion field
    3. If outdated: apply migration chain
    4. If --dry-run: report what would change without modifying
    5. Backup originals as .bak before migrating
    """
    outdated = []
    for subdir in ["ast", "semantics", "locked", "architecture"]:
        for fname in state.list_artifacts(subdir, ".json"):
            data = state.read_artifact(subdir, fname)
            if data and check_version(data) is not None:
                outdated.append((subdir, fname, data.get("schemaVersion", "1.0")))

    if not outdated:
        console.print("[green]All artifacts at current schema version.[/]")
        return

    console.print(f"Found {len(outdated)} artifacts needing migration")

    if dry_run:
        for subdir, fname, version in outdated:
            console.print(f"  {subdir}/{fname}: {version} → {SCHEMA_VERSION}")
        return

    for subdir, fname, version in outdated:
        data = state.read_artifact(subdir, fname)
        # Backup
        backup_path = state.modernize_dir / subdir / (fname + ".bak")
        backup_path.write_text(json.dumps(data, indent=2))
        # Migrate
        migrated = migrate_artifact(data)
        state.write_artifact(subdir, fname, migrated)

    console.print(f"[green]Migrated {len(outdated)} artifacts. Originals saved as .bak[/]")
```

---

## 11. Testing Strategy

### 11.1 Test Framework

Same as original IMPLEMENTATION-PLAN.md Section 11.1–11.2.

### 11.2 Additional Test Cases (New Risks)

**Encoding Detection** (`tests/unit/test_encoding.py`):
```python
def test_detect_windows_1252(tmp_path):
    """Risk 23: Detect and normalize Windows-1252 encoding."""
    f = tmp_path / "test.cfc"
    f.write_bytes(b'<cfset name = "caf\xe9">')  # Latin-1 é

    detector = EncodingDetector()
    content, encoding, confidence = detector.detect_and_read(f)

    assert "café" in content
    assert encoding in ("windows-1252", "iso-8859-1", "latin-1")

def test_reject_binary(tmp_path):
    """Risk 23: Binary files are rejected."""
    f = tmp_path / "image.cfc"
    f.write_bytes(b'\x89PNG\x00\x00\x00\r')

    detector = EncodingDetector()
    assert detector.is_binary(f) == True
```

**File Locking** (`tests/unit/test_file_lock.py`):
```python
def test_acquire_and_release(tmp_path):
    """Risk 28: Basic lock acquire/release."""
    lock_mgr = FileLock(tmp_path)
    lock = lock_mgr.acquire("extract", "global")
    assert (tmp_path / "extract-global.lock").exists()
    lock_mgr.release("extract", "global")
    assert not (tmp_path / "extract-global.lock").exists()

def test_concurrent_lock_blocked(tmp_path):
    """Risk 28: Second acquire raises ConcurrencyError."""
    lock_mgr = FileLock(tmp_path)
    lock_mgr.acquire("extract", "global")
    with pytest.raises(ConcurrencyError):
        lock_mgr.acquire("extract", "global")
    lock_mgr.release("extract", "global")

def test_stale_lock_detected(tmp_path):
    """Risk 28: Stale lock from dead PID is detected."""
    lock_mgr = FileLock(tmp_path)
    # Write a lock with a fake PID
    fake_lock = {"step": "extract", "scope": "global", "pid": 99999999, "holder": "test"}
    (tmp_path / "extract-global.lock").write_text(json.dumps(fake_lock))

    stale = lock_mgr.check_stale()
    assert len(stale) == 1
```

**Checkpoint Recovery** (`tests/unit/test_checkpoint.py`):
```python
def test_resume_from_checkpoint(tmp_path):
    """Risk 15: Resume extraction after crash."""
    mgr = CheckpointManager(tmp_path)
    cp = mgr.create("extract", ["A", "B", "C", "D", "E"])
    mgr.update("extract", "A", success=True)
    mgr.update("extract", "B", success=True)
    mgr.set_current("extract", "C")

    # Simulate crash — checkpoint shows C in progress, D/E remaining
    resumable = mgr.get_resumable("extract")
    assert resumable == ["C", "D", "E"]  # C re-processed from scratch

def test_retry_failed(tmp_path):
    """Risk 15: Retry only failed modules."""
    mgr = CheckpointManager(tmp_path)
    cp = mgr.create("extract", ["A", "B", "C"])
    mgr.update("extract", "A", success=True)
    mgr.update("extract", "B", success=False, error="timeout")
    mgr.update("extract", "C", success=True)

    cp = mgr.load("extract")
    assert len(cp.failed) == 1
    assert cp.failed[0]["module"] == "B"
```

**Hash Chain Audit** (`tests/unit/test_hash_chain.py`):
```python
def test_audit_chain_integrity(tmp_path):
    """Risk 26: Verify hash chain is intact."""
    logger = AuditLogger(tmp_path)
    logger.log("approve", "UserService", "john@test.com", {})
    logger.log("lock", "UserService", "koustubh", {"checksum": "abc"})
    logger.log("ai_call", "UserService", "ai:claude", {"tokens": 100})

    intact, break_point = logger.verify_chain()
    assert intact == True
    assert break_point == -1

def test_audit_chain_tamper_detection(tmp_path):
    """Risk 26: Tampering is detected."""
    logger = AuditLogger(tmp_path)
    logger.log("approve", "UserService", "john@test.com", {})
    logger.log("lock", "UserService", "koustubh", {})

    # Tamper with entry 1
    entry_file = tmp_path / "entries" / "000001.json"
    data = json.loads(entry_file.read_text())
    data["actor"] = "TAMPERED"
    entry_file.write_text(json.dumps(data))

    intact, break_point = logger.verify_chain()
    assert intact == False
    assert break_point == 1
```

**Confidence Scoring** (`tests/unit/test_confidence.py`):
```python
def test_deterministic_gets_100():
    """Risk 5: Deterministic extraction = 100% confidence."""
    scorer = ConfidenceScorer()
    func = SemanticFunction(name="test", signature={},
                           business_rule=BusinessRule(name="t", description="t", source="deterministic"))
    ast_func = ASTFunction(name="test", access="public", return_type="void")
    assert scorer.score_function(func, ast_func) == 100

def test_ai_with_evidence_floored_at_85():
    """Risk 5: AI-assisted with AST evidence gets at least 85."""
    scorer = ConfidenceScorer()
    func = SemanticFunction(name="test", signature={},
                           business_rule=BusinessRule(name="t", description="t", source="ai", confidence=70))
    ast_func = ASTFunction(name="test", access="public", return_type="void",
                          queries=[ASTQuery(name="q", sql="SELECT 1", tables=["t"], operation="SELECT")])
    assert scorer.score_function(func, ast_func, ai_confidence=70) == 85

def test_pure_ai_capped_at_80():
    """Risk 5: Pure AI inference capped at 80."""
    scorer = ConfidenceScorer()
    func = SemanticFunction(name="test", signature={},
                           business_rule=BusinessRule(name="t", description="t", source="ai", confidence=95))
    ast_func = ASTFunction(name="test", access="public", return_type="void")
    assert scorer.score_function(func, ast_func, ai_confidence=95) == 80
```

**Cross-Module Consistency** (`tests/integration/test_pipeline_flow.py`):
```python
def test_consistency_check_detects_mismatch(tmp_project):
    """Risk 1: Detect argument count mismatch across modules."""
    # Create two semantic models where caller and callee disagree
    # ... write fixtures ...
    _run_consistency_check(tmp_project)
    report = tmp_project.read_artifact("semantics", "consistency-report.json")
    assert len(report["mismatches"]) > 0
```

---

## 12. Error Handling Contract

Same as original IMPLEMENTATION-PLAN.md Section 12, with this addition:

### 12.5 Concurrent Access Failures (Risk 28)

```python
try:
    lock = file_lock.acquire("extract", "global")
except ConcurrencyError as e:
    console.print(f"[red]Pipeline locked:[/] {e.lock_holder} is running (PID in {e.lock_file})")
    console.print("Use 'modernize unlock-pipeline' if the previous run crashed.")
    raise SystemExit(1)
```

---

## 13. Implementation Order Within Each Phase

### Phase 1 (Foundation):
1. `core/errors.py` — exception hierarchy (including new types)
2. `core/utils.py` — to_camel_case, atomic_write_json, hash helpers
3. `core/models.py` — all dataclasses with to_dict/from_dict
4. `core/schema_version.py` — versioning + migration registry (Risk 20)
5. `core/state.py` — ProjectState (with schema version checking)
6. `core/encoding.py` — encoding detection (Risk 23)
7. `core/file_lock.py` — advisory file locking (Risk 28)
8. `core/sanitizer.py` — Sanitizer
9. `core/audit.py` — AuditLogger with hash chain (Risk 26)
10. `core/confidence.py` — ConfidenceScorer (Risk 5)
11. `core/checkpoint.py` — CheckpointManager (Risk 15)
12. `core/cost.py` — CostTracker (Risk 16)
13. `providers/base.py` — AIProvider interface
14. `providers/claude.py` — Claude adapter
15. `providers/openai_provider.py` — OpenAI adapter
16. `providers/gemini.py` — Gemini adapter
17. `providers/__init__.py` — factory function
18. `core/chunker.py` — Chunker
19. `core/context_assembler.py` — ContextAssembler
20. `core/aggregator.py` — ResultAggregator with dedup (Risk 4)
21. `agents/loader.py`, `agents/resolver.py`, `agents/registry.py`
22. `modernize.py` — CLI skeleton with `init`, `status`, `audit`, `audit --verify`, `audit --cost`, `config budget`, `config concurrency`, `unlock-pipeline`, `migrate`
23. Tests for all of the above

### Phase 2 (Parser + Extractor):
1. `adapters/source/base.py` — SourceAdapter interface (updated with config_patterns, locale functions, adapter version)
2. `adapters/source/coldfusion/sql_extractor.py` — SQL parsing
3. `adapters/source/coldfusion/config_parser.py` — Config capture (Risk 18)
4. `adapters/source/coldfusion/parser.py` — ColdFusion parser (with graceful degradation Risk 21, locale detection Risk 24)
5. `adapters/source/coldfusion/adapter.py` — ColdFusionAdapter
6. Agent YAML files (all 7)
7. `pipeline/parser.py` — Step 1 (with encoding detection Risk 23, incremental Risk 11, config capture Risk 18, asset scan Risk 25, adapter version Risk 22)
8. `pipeline/extractor.py` — Step 2 (with consistency check Risk 1, confidence scoring Risk 5, checkpoint Risk 15, dry-run Risk 16)
9. `pipeline/documenter.py` — Step 3
10. `pipeline/reviewer.py` — Step 4 (with conflict resolution Risk 19, correction cascade Risk 2)
11. `pipeline/import_schema.py` — import-schema command (Risk 13)
12. CLI commands: `parse`, `parse --incremental`, `parse --force`, `parse --coverage-report`, `extract`, `extract --dry-run`, `extract --retry-failed`, `document`, `review`, `correct`, `approve`, `import-schema`, `config encoding`, `config reviewers --assign`
13. Tests: parser (critical), encoding, extractor, consistency check, conflict resolution

### Phase 3 (Lock + Architect):
1. `pipeline/locker.py` — lock/unlock/verify (per-module granularity Risk 3, incremental hash check Risk 11)
2. `pipeline/architect.py` — existing architecture (5b), target stack config (5c), target architecture (5d), URL mappings (Risk 27)
3. CLI commands: `lock semantics`, `unlock semantics [module]`, `architect --existing`, `config target-stack`, `architect --target`, `review architect`, `approve architect`, `lock architecture`, `status --stale`
4. Tests: lock integrity, per-module unlock, stale detection, architecture split

### Phase 4 (Generator):
1. `adapters/target/base.py` — TargetAdapter interface
2. `adapters/target/react/` — React adapter + scaffolder + conventions
3. `adapters/target/go/` — Go adapter + scaffolder + conventions
4. `pipeline/generator.py` — Step 6 (with generation baseline Risk 12, asset copy Risk 25, proxy config Risk 27, locale-aware generation Risk 24, file locking Risk 28)
5. Client component registry (YAML manifests)
6. CLI commands: `generate`, `review generate`, `components register`
7. Tests: generation with mock provider, human edit detection

### Phase 5 (Verifier):
1. `pipeline/recorder.py` — HTTP recording proxy (Risk 17)
2. `pipeline/verifier.py` — Step 7 (with replay Risk 17, architecture conformance Risk 6, escalation paths Risk 7)
3. CLI commands: `record`, `verify`, `verify --replay`, `reject verify --escalate`
4. Tests: replay diffing, conformance checking

### Phase 6 (Polish):
1. `pipeline/runner.py` — auto mode with calibration gate (Risk 14)
2. `pipeline/reporter.py` — `status`, `report --weekly`
3. Schema migration CLI — `migrate`, `migrate --dry-run` (Risk 20)
4. Reviewer assignment from git blame (Risk 19)
5. Selective adapter re-parse from changelog (Risk 22 optimization)
6. Stale lock detection + `unlock-pipeline` (Risk 28)
7. Audit trail verification — `audit --verify` (Risk 26)
8. Human annotation system
9. Confidence scoring integration
10. Execution mode logic (guided/supervised/auto)
11. Full end-to-end integration test

---

## 14. CLI Command Reference

Complete list of all CLI commands with signatures:

```
# Phase 1: Foundation
modernize init <source_path> --source-adapters <list> --target-stack <spec> --provider <name> [--model <name>] [--trust-level strict|standard|trust] [--execution-mode guided|supervised|auto]
modernize status [--stale]
modernize audit [--cost] [--verify]
modernize config budget --max-total <amount> [--warn-at <amount>]
modernize config concurrency --max-parallel <N> [--rate-limit <N>/min]
modernize config encoding <file> --encoding <encoding>
modernize unlock-pipeline <step>
modernize migrate [--dry-run]

# Phase 2: Parser + Extractor
modernize parse [--incremental] [--force] [--coverage-report]
modernize extract [--dry-run] [--retry-failed]
modernize document
modernize review semantics [<module>] [--prioritized]
modernize correct <module.function> --field <field> --value <value> [--reviewer <email>]
modernize add-rule <module.function> --name <name> --description <desc>
modernize approve semantics <module> [--all]
modernize import-schema --connection <conn_string> [--include-procs]
modernize config reviewers --assign <module> <email>

# Phase 3: Lock + Architect
modernize lock semantics
modernize unlock semantics [<module>] [--force]
modernize architect --existing
modernize config target-stack --frontend <adapter> --backend <adapter> [--workers <adapter>]
modernize architect --target
modernize review architect
modernize approve architect
modernize lock architecture

# Phase 4: Generator
modernize generate <service>
modernize review generate <service>
modernize components register <path>

# Phase 5: Verifier
modernize record <service> --proxy-port <port> --duration <minutes> [--legacy-url <url>]
modernize verify <service> [--replay]
modernize reject verify <service> [--escalate semantics|architecture]

# Phase 6: Polish
modernize run --all [--force-auto]
modernize summary
modernize report [--weekly]
modernize annotate <module> --note <text>
modernize redact review
modernize redact add <category>
modernize redact remove <category>
modernize redact add-pattern <pattern>
```

---

## Appendix A: Risk-to-Implementation Cross-Reference

| Risk | Description | Files | Phase |
|------|-------------|-------|-------|
| 1 | Cross-module consistency | `pipeline/extractor.py` | 2 |
| 2 | Correction cascade | `pipeline/reviewer.py` | 2 |
| 3 | Partial lock | `pipeline/locker.py` | 3 |
| 4 | Chunking dedup | `core/aggregator.py` | 1 |
| 5 | Confidence calibration | `core/confidence.py` | 1 |
| 6 | Architecture conformance | `pipeline/verifier.py` | 5 |
| 7 | Verify escalation paths | `pipeline/verifier.py` | 5 |
| 8 | Review fatigue | `pipeline/runner.py` (auto-approve thresholds) | 6 |
| 9 | DB migration | OUT OF SCOPE | — |
| 10 | Mixed-language | `adapters/source/base.py`, `pipeline/parser.py` | 2 |
| 11 | Incremental processing | `core/models.py` (hash fields), `pipeline/parser.py` | 2 |
| 12 | Human edit overwrite | `pipeline/generator.py` | 4 |
| 13 | Stored procedures | `pipeline/import_schema.py` | 2 |
| 14 | Auto mode constraints | `pipeline/runner.py` | 6 |
| 15 | Pipeline recovery | `core/checkpoint.py` | 1 |
| 16 | Cost estimation | `core/cost.py` | 1 |
| 17 | Behavioral verification | `pipeline/recorder.py`, `pipeline/verifier.py` | 5 |
| 18 | Config capture | `adapters/source/coldfusion/config_parser.py` | 2 |
| 19 | Reviewer conflicts | `pipeline/reviewer.py` | 2+6 |
| 20 | Schema versioning | `core/schema_version.py` | 1+6 |
| 21 | Grammar gaps | `adapters/source/coldfusion/parser.py` | 2 |
| 22 | Adapter versioning | `adapters/source/base.py` | 1+2 |
| 23 | File encoding | `core/encoding.py` | 1+2 |
| 24 | Locale/timezone | `adapters/source/coldfusion/config_parser.py`, `pipeline/generator.py` | 2+4 |
| 25 | Static assets | `pipeline/parser.py` | 2+4 |
| 26 | Audit integrity | `core/audit.py` | 1+6 |
| 27 | URL mapping | `pipeline/architect.py`, `pipeline/generator.py` | 3+4 |
| 28 | Concurrent runs | `core/file_lock.py` | 1+6 |

---

## Appendix B: Key Behavioral Notes for Implementors

1. **JSON output keys are camelCase** — every `to_dict()` must convert snake_case.
2. **ColdFusion parser: regex fallback** — use regex if tree-sitter-cfml unavailable.
3. **AI calls must always have fallbacks** — pipeline never crashes on AI failure.
4. **Locks are checksummed** — SHA-256 with tamper detection.
5. **Corrections modify BOTH files** — corrections JSON + semantic model JSON.
6. **Provider packages imported lazily** — only when selected.
7. **Auto mode stops on verify failure** — but flags low-confidence items without stopping.
8. **File writes are atomic** — write-to-temp-then-rename pattern everywhere.
9. **Architecture blueprint split** — existing-architecture.md + target-architecture.md (two separate documents).
10. **Generator produces multiple files** — handlers, store, models, auth, API client per service.
11. **Per-module locking** — not monolithic. Unlock one module without invalidating others.
12. **Adapter version stamps every AST** — adapter code change triggers re-parse.
13. **Schema version stamps every artifact** — CLI upgrade triggers migration prompt.
14. **Hash chain on audit log** — tamper-evident, not tamper-proof.
15. **GUI/dashboard is out of scope** — CLI-only tool.
16. **DB migration is out of scope** — framework captures data access patterns but does not generate schema changes.
