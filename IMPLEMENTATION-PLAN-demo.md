# Implementation Plan — Demo Modernization Tool (ColdFusion to Python + React)

> Audience: another AI coding agent that should be able to start implementing immediately.
>
> Source of truth for scope: [DEMO-PLAN.md](/Users/koustubh/Documents/modern-app/DEMO-PLAN.md)
>
> Primary codebase to extend: [app](/Users/koustubh/Documents/modern-app/app)
>
> Key implementation constraint: the demo tool itself must be written in Python.

---

## 1. Purpose

Build a runnable demo modernization tool that:

- ingests a small ColdFusion codebase
- produces deterministic AST and fact artifacts
- derives reviewable semantics
- enforces semantic, source-architecture, and target-architecture locks
- generates a small runnable Python + React target application
- emits verification and audit artifacts

The goal is not to fully productionize the platform. The goal is to implement enough of the workflow so the demo is believable, inspectable, and runnable end-to-end.

---

## 2. Non-Goals

Do not expand this implementation into any of the following:

- a full ColdFusion parser
- a generalized adapter marketplace
- a production-grade invalidation engine
- a full cutover automation system
- a full multi-project orchestration platform
- freeform AI document writing without structured artifacts

When in doubt, prefer a narrower, clearer implementation that preserves the workflow shape.

---

## 3. Core Principles For The Implementation

### 3.1 Code quality

The code should be:

- easy to read
- explicit rather than clever
- heavily structured around small modules
- straightforward to test
- easy for another AI or engineer to continue

Prefer:

- simple dataclasses
- pure functions where practical
- clear artifact schemas
- thin CLI handlers that call pipeline modules

Avoid:

- large monolithic functions
- hidden state
- tightly coupled CLI and business logic
- magic constants scattered through the codebase

### 3.2 Determinism boundaries

Treat these as deterministic:

- source/config discovery
- AST persistence
- fact extraction
- artifact writing
- review state persistence
- lock creation
- stale-lock detection
- state transitions

Treat these as AI-assisted or heuristic but still structured:

- semantic derivation
- architecture reasoning
- narrative parts of generated documents
- target code generation

The implementation must keep these boundaries obvious in both code and artifact structure.

### 3.3 Test discipline

Every phase must end with:

- unit tests for the new logic in that phase
- at least one end-to-end test of the pipeline behavior available up to that phase

Do not defer tests until the end.

---

## 4. Existing Baseline

The current implementation already exists under [app](/Users/koustubh/Documents/modern-app/app) and contains:

- a Python CLI in [modernize.py](/Users/koustubh/Documents/modern-app/app/modernize.py)
- project state management in [state.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/state.py)
- core models in [models.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/models.py)
- pipeline modules in [pipeline/](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline)
- source and target adapters in [adapters/](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters)
- Markdown templates in [templates/](/Users/koustubh/Documents/modern-app/app/modernize_demo/templates)
- tests in [tests/](/Users/koustubh/Documents/modern-app/app/tests)
- sample/demo inputs in [tests/fixtures/](/Users/koustubh/Documents/modern-app/app/tests/fixtures)

This implementation plan should now be treated as a regeneration and maintenance plan for `app`.

---

## 5. Target End State

By the end of implementation, the demo should support a flow like:

```bash
cd app
python3 modernize.py init ./tests/fixtures/sample_app
python3 modernize.py choose-provider
python3 modernize.py discover
python3 modernize.py parse
python3 modernize.py facts
python3 modernize.py extract
python3 modernize.py review semantics
python3 modernize.py approve semantics --all
python3 modernize.py lock semantics
python3 modernize.py source-architect
python3 modernize.py review source-architecture
python3 modernize.py approve source-architecture
python3 modernize.py lock source-architecture
python3 modernize.py choose-target-stack --target-stack python:backend,react:frontend
python3 modernize.py target-architect
python3 modernize.py review target-architecture
python3 modernize.py approve target-architecture
python3 modernize.py lock target-architecture
python3 modernize.py generate demo-app
python3 modernize.py verify demo-app
python3 modernize.py status
```

The exact command names can vary slightly, but the implemented behavior must cover those stages.

---

## 6. Proposed Directory Structure Changes

The implemented directory shape is now:

```text
app/
├── modernize.py
├── modernize_demo/
│   ├── core/
│   │   ├── models.py
│   │   ├── state.py
│   │   ├── audit.py
│   │   ├── hashing.py
│   │   ├── invalidation.py
│   │   └── rendering.py
│   ├── adapters/
│   ├── __init__.py
│   ├── source/
│   │   ├── __init__.py
│   │   ├── coldfusion.py
│   │   └── discovery.py
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── prompting.py
│   │   ├── demo_provider.py
│   │   ├── command_provider.py
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── gemini_provider.py
│   │
│   └── target/
│       ├── __init__.py
│       ├── python_backend.py
│       └── react_frontend.py
│   ├── pipeline/
│   │   ├── discover.py
│   │   ├── parser.py
│   │   ├── facts.py
│   │   ├── extractor.py
│   │   ├── reviewer.py
│   │   ├── locker.py
│   │   ├── source_architect.py
│   │   ├── target_architect.py
│   │   ├── documenter.py
│   │   ├── generator.py
│   │   └── verifier.py
│   └── templates/
│       ├── source_architecture.md.j2
│       └── target_architecture.md.j2
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── doitlive/
│   └── happy-path.sh
├── requirements.txt
├── README.md
├── .venv/
├── tests/
└── .modernize/
    ├── discovery/
    ├── ast/
    ├── facts/
    ├── semantics/
    ├── architecture/
    ├── docs/
    ├── corrections/
    ├── locked/
    ├── services/
    ├── recordings/
    └── audit/
```

Notes:

- `source_architect.py` and `target_architect.py` are intentionally separate.
- `facts.py` is a first-class deterministic stage.
- `documenter.py` renders controlled Markdown templates and Mermaid diagrams from artifacts.
- AI provider code lives under `modernize_demo/adapters/ai/`.

---

## 7. Artifact Model To Implement

These artifact types must exist in a visible way for the demo.

### 7.0 Demo slice manifest

Path:

- `.modernize/discovery/demo-slice.json`

Purpose:

- record the currently selected working subset of the discovered ColdFusion estate
- make later stages explicit about which files/modules are in scope

Contents:

- selected file paths
- selected modules
- selection method (`manual`, `inferred`, or `all_discovered`)
- optional rationale
- source discovery checksum used when the slice was defined

### 7.1 Discovery artifact

Path:

- `.modernize/discovery/source-discovery.json`

Contents:

- discovered source files
- discovered config files
- environment assumptions
- source adapter name/version
- source hash summary

### 7.2 AST artifacts

Path pattern:

- `.modernize/ast/<module>.ast.json`

Contents:

- parse status
- source file path
- source hash
- adapter version
- structured parse result
- diagnostics / unsupported patterns

### 7.3 Fact artifacts

Path pattern:

- `.modernize/facts/<module>.facts.json`

Contents:

- module name
- file path
- reads/writes
- tables touched
- session/config usage
- calls/includes
- endpoints/actions inferred
- inference notes where convention-based fields were inferred

### 7.4 Semantic artifacts

Path pattern:

- `.modernize/semantics/<module>.semantic.json`

Contents:

- semantic meaning
- business rules
- dependencies
- confidence
- source of each field if useful (`deterministic`, `ai`, `human`)
- approval metadata after review

### 7.5 Source architecture artifact

Canonical machine artifact:

- `.modernize/architecture/source-architecture.json`

Rendered doc:

- `.modernize/architecture/source-architecture.md`

Contents:

- graph-shaped nodes and edges
- modules and responsibilities
- tables/state/config dependencies
- coupling hotspots
- source lock metadata when applicable

### 7.6 Target architecture artifact

Canonical machine artifact:

- `.modernize/architecture/target-architecture.json`

Rendered doc:

- `.modernize/architecture/target-architecture.md`

Contents:

- target components/services
- API contracts
- data ownership
- source-to-target mappings
- generation boundaries
- target lock metadata when applicable

### 7.7 Lock artifacts

Required lock files:

- `.modernize/locked/semantic-lock.json`
- `.modernize/locked/source-architecture-lock.json`
- `.modernize/locked/target-architecture-lock.json`
- `.modernize/locked/lock-manifest.json`

Each lock should include:

- lock type
- version
- locked at
- locked by
- upstream artifact checksums
- relevant approval metadata

### 7.7a Review state artifacts

Review state must be explicit before each lock exists.

Required review-state files:

- `.modernize/semantics/review-state.json`
- `.modernize/architecture/source-architecture-review.json`
- `.modernize/architecture/target-architecture-review.json`

Each review-state artifact should include:

- status (`pending`, `approved`, `rejected`, `stale`)
- approved by
- approved at
- comments or corrections
- checksum of the artifact being reviewed
- any unresolved items

### 7.8 Audit artifact

Path:

- `.modernize/audit/audit-log.jsonl`

Each line should contain:

- timestamp
- stage
- action
- artifact references
- result

### 7.9 Verification artifact

Path:

- `.modernize/recordings/<service>/verification-report.json`

Contents:

- scenarios checked
- expected behavior
- observed/generated behavior
- conformance summary
- verdict

---

## 7.10 Lock Scope Decision For The Demo

For the demo, lock scope should be all-or-nothing within the selected demo slice.

That means:

- every module in the selected slice must be approved before semantic lock succeeds
- source architecture review must be approved before source-architecture lock succeeds
- target architecture review must be approved before target-architecture lock succeeds

Downstream stages must consume the selected-slice locks as complete approved baselines, not partially approved subsets.

This is the right choice for the demo because it is easier to explain and avoids partial-lock ambiguity.

---

## 8. Tests To Create

Create and maintain a proper `tests/` tree under `app`.

### 8.1 Unit tests

Expected coverage areas:

- source discovery helpers
- AST parser wrapper / adapter behavior
- fact extraction transforms
- AI provider registry and provider adapters
- semantic review state transitions
- lock creation and checksum generation
- stale-lock detection
- source-architecture rendering
- target-architecture rendering
- audit logging
- generator gating logic
- verification result shaping

### 8.2 Integration tests

Expected end-to-end coverage:

- init -> discover -> parse
- parse -> facts -> extract
- provider selection -> extract
- review -> approve -> lock semantics
- source architecture -> review -> approve -> lock
- target architecture -> review -> approve -> lock
- generation blocked without required locks
- generation succeeds with all locks present
- stale-lock detection blocks downstream work
- verify produces report artifact

### 8.3 Test fixtures

Add fixtures for:

- small ColdFusion files
- sample config/env inputs
- expected AST outputs
- expected fact outputs
- expected semantic outputs
- expected target architecture artifacts

Use the current fixture app under [tests/fixtures](/Users/koustubh/Documents/modern-app/app/tests/fixtures) as a starting point, but keep tests decoupled from the live `.modernize` state.

---

## 9. Dependencies

Keep dependencies minimal, but align with the current implementation.

### 9.1 Required

- `jinja2`
- `tree-sitter`
- `tree-sitter-language-pack`
- `doitlive`
- `openai`
- `anthropic`
- `google-genai`

### 9.2 Current testing approach

- Python standard library `unittest`
- fixture-based integration tests under [app/tests](/Users/koustubh/Documents/modern-app/app/tests)

### 9.3 Parsing requirement

- ColdFusion parsing should remain Tree-sitter based.
- Do not regress to regex-only parsing in regenerated code.
- Heuristics are acceptable only after parse-tree extraction, for normalization or unsupported-pattern handling.

### 9.4 AI provider requirement

- Semantic derivation must remain provider-driven behind a common interface.
- The tool must support:
  - `demo-ai`
  - `openai`
  - `anthropic`
  - `gemini`
  - `command-json`
  - `python:<module>:<symbol>`
- Gemini must support both:
  - API key auth
  - Google Application Default Credentials / Vertex AI, including personal credentials from `gcloud auth application-default login`

### 9.5 Avoid unless necessary

- heavy web frameworks
- databases
- job queues
- external services required for test execution

---

## 10. Phase Plan

Implement in the phases below, in order.

Each phase ends with:

- code complete for that phase
- unit tests green
- at least one end-to-end test green
- README or command examples updated if behavior changed materially

---

## Phase 1 — Stabilize The Demo Foundation

### Goal

Turn `app` into a clean, testable baseline before adding major behavior.

### Work

1. Create or stabilize `tests/unit`, `tests/integration`, and `tests/fixtures` under `app/`.
2. Add simple `unittest` runner instructions to [README.md](/Users/koustubh/Documents/modern-app/app/README.md).
3. Refactor the CLI so command handlers are thin and pipeline modules hold behavior.
4. Extend `ProjectState.init()` to create all required artifact directories:
   - `discovery`
   - `facts`
   - `audit`
   - ensure architecture and locked dirs match the target model
5. Add a small audit logging helper in `core/audit.py`.
6. Add a small hashing helper in `core/hashing.py`.
7. Extend the state schema so pipeline state can track:
   - selected demo slice
   - selected AI provider
   - review status for semantics
   - review status for source architecture
   - review status for target architecture
   - stale/valid markers for locks
8. Add baseline tests for state initialization and artifact writing.

### Files likely touched

- [README.md](/Users/koustubh/Documents/modern-app/app/README.md)
- [state.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/state.py)
- [modernize.py](/Users/koustubh/Documents/modern-app/app/modernize.py)
- [audit.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/audit.py)
- [hashing.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/hashing.py)
- new tests

### Unit tests

- state init creates required directories
- artifact read/write works
- audit logger appends valid lines
- checksum helper is deterministic
- migration state contains placeholders for slice selection and review-state tracking

### End-to-end test

- `init` produces `.modernize/` with the expected structure and initial migration state

### Phase exit criteria

- clean project baseline exists
- tests run locally with `python -m unittest`
- audit and hashing helpers are available for later phases

---

## Phase 2 — Discovery, Source Adapter, AST, And Facts

### Goal

Make source intake real enough to produce visible discovery, AST, and fact artifacts from arbitrary small ColdFusion inputs.

### Work

1. Add `adapters/source/coldfusion.py` with a narrow but explicit adapter API:
   - discover files
   - parse file
   - extract facts from parsed structure
2. Add `pipeline/discover.py`.
3. Add a new `discover` CLI command.
4. Add a simple demo-slice selection rule and persist it in `.modernize/discovery/demo-slice.json`.
   - Default behavior should be `all_discovered` until a narrower slice-selection command exists.
   - Later stages must read this manifest rather than guessing scope.
5. Split fact extraction into a dedicated `pipeline/facts.py` stage and CLI command.
6. Update parser stage so it writes actual AST artifacts per file.
7. Add a source/config discovery artifact that records:
   - input files
   - config files
   - environment assumptions
8. Record diagnostics for unsupported constructs rather than failing silently.
9. Keep the parse stage Tree-sitter based.

### Adapter API shape

Use methods similar to:

```python
class ColdFusionSourceAdapter:
    name: str
    version: str

    def discover(self, source_root: Path) -> DiscoveryArtifact: ...
    def parse_file(self, file_path: Path) -> ASTArtifact: ...
    def extract_facts(self, ast: ASTArtifact) -> FactArtifact: ...
```

Implementation rule:

- use Tree-sitter-backed parsing for ColdFusion inputs
- do not regress to regex-only source parsing
- heuristics are acceptable only after parse-tree extraction

### Files likely added/changed

- [coldfusion.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/source/coldfusion.py)
- [discover.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/discover.py)
- [facts.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/facts.py)
- [parser.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/parser.py)
- [models.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/models.py)
- [modernize.py](/Users/koustubh/Documents/modern-app/app/modernize.py)

### Unit tests

- discovery finds ColdFusion files
- AST artifacts include source hash and adapter version
- fact extraction captures DB/state/call relationships for fixture inputs
- unsupported constructs are surfaced in diagnostics
- demo-slice manifest is written and later stages can load it

### End-to-end test

- `init -> discover -> parse -> facts` produces:
  - `source-discovery.json`
  - `demo-slice.json`
  - one or more `.ast.json` files
  - one or more `.facts.json` files

### Phase exit criteria

- a user can point the tool at a small ColdFusion directory and get deterministic discovery/AST/fact artifacts

---

## Phase 3 — Semantic Extraction, Review, And Semantic Lock

### Goal

Turn facts into reviewable semantics and make the first lock feel real.

### Work

1. Update `pipeline/extractor.py` so it consumes fact artifacts explicitly.
2. Make semantic artifacts include provenance fields where helpful:
   - `source`
   - `confidence`
   - `approved`
3. Keep AI derivation provider-driven and structured.
4. Maintain a common provider interface under `adapters/ai/base.py`.
5. Resolve provider strings through `adapters/ai/registry.py`.
6. Keep `demo-ai` as the default fallback, but support switching providers with `choose-provider`.
7. Improve `pipeline/reviewer.py` so semantic review can:
   - list modules
   - show module semantics
   - generate one semantic review document per module
   - generate an index document for scalable review
   - accept a small correction
   - approve a module or all modules
8. Update `pipeline/locker.py` so semantic lock:
   - requires all modules in the selected demo slice to be approved
   - records checksums of semantic artifacts
   - writes a lock manifest entry
   - logs to audit
9. Persist semantic review state in `.modernize/semantics/review-state.json`.
10. Render semantic review docs under:
   - `.modernize/docs/semantic-review/index.md`
   - `.modernize/docs/semantic-review/modules/<module>.md`
11. Warn during `extract` if the current provider is still `demo-ai`.
12. Support native providers for:
   - OpenAI
   - Anthropic
   - Gemini
13. Support generic provider modes for:
   - `command-json`
   - `python:<module>:<symbol>`
14. Gemini must support both API-key auth and ADC / Vertex AI auth.

### Files likely touched

- [extractor.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/extractor.py)
- [reviewer.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/reviewer.py)
- [locker.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/locker.py)
- [models.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/models.py)
- [base.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/base.py)
- [registry.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/registry.py)
- native provider files under [adapters/ai](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai)

### Unit tests

- semantic artifacts serialize and deserialize correctly
- provider registry resolves supported provider strings
- provider adapters shape normalized semantic output correctly
- semantic review index and module docs are rendered correctly
- approval state is persisted correctly
- correction flow updates the right semantic fields
- semantic lock fails when approval is incomplete
- semantic lock writes expected checksums
- semantic lock only considers modules in the selected demo slice

### End-to-end test

- `discover -> parse -> facts -> extract -> review semantics -> approve semantics -> lock semantics` succeeds and writes lock files and semantic review docs

### Phase exit criteria

- semantic review and lock are both visible, meaningful, and test-covered

---

## Phase 4 — Source Architecture, Review, Lock, And Document Rendering

### Goal

Implement source architecture as a first-class stage and render a deterministic Markdown document with Mermaid diagrams.

### Work

1. Add `pipeline/source_architect.py`.
2. Derive a graph-shaped source architecture artifact from locked semantics and facts.
3. Render `.modernize/architecture/source-architecture.md` using a deterministic template.
4. Generate Mermaid diagrams from the structured source architecture artifact.
5. Add review and approval commands for source architecture.
6. Persist source-architecture review state in `.modernize/architecture/source-architecture-review.json`.
7. Add source-architecture lock support in `pipeline/locker.py`.
8. Update the lock manifest to include source-architecture lock.
9. Add an audit entry for source-architecture generation, approval, and lock.

### Suggested source architecture schema

At minimum:

```json
{
  "nodes": [],
  "edges": [],
  "modules": [],
  "tables": [],
  "stateDependencies": [],
  "configDependencies": [],
  "hotspots": [],
  "generatedFrom": {
    "semanticLockChecksum": "",
    "factChecksums": []
  }
}
```

### Files likely added/changed

- [source_architect.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/source_architect.py)
- [source_architecture.md.j2](/Users/koustubh/Documents/modern-app/app/modernize_demo/templates/source_architecture.md.j2)
- [documenter.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/documenter.py)
- [locker.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/locker.py)
- [modernize.py](/Users/koustubh/Documents/modern-app/app/modernize.py)

### Unit tests

- source architecture artifact contains expected nodes and edges from fixture semantics
- rendered source architecture doc includes key sections
- Mermaid blocks are present and deterministic
- source architecture lock fails without approval
- source architecture review-state artifact is updated correctly on approval

### End-to-end test

- `... -> lock semantics -> source-architect -> approve source-architecture -> lock source-architecture`

### Phase exit criteria

- source architecture exists as:
  - machine artifact
  - rendered Markdown document
  - lockable reviewed stage

---

## Phase 5 — Target Stack Choice And Architecture Inputs

### Goal

Make target stack choice explicit and enforce the design rule that it happens only after source-architecture lock.

### Work

1. Add a `choose-target-stack` CLI command.
2. Persist stack choice in `.modernize/architecture/target-stack.json`.
3. Block `target-architect` until source-architecture lock exists.
4. Block `target-architect` until a target stack has been chosen.
5. Keep target stack out of `init`.

### Files likely touched

- [modernize.py](/Users/koustubh/Documents/modern-app/app/modernize.py)
- [target_architect.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/target_architect.py)
- [state.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/state.py)

### Unit tests

- `choose-target-stack` writes the expected artifact
- target architecture generation is blocked before source-architecture lock
- target architecture generation is blocked before target-stack choice

### End-to-end test

- `... -> lock source-architecture -> choose-target-stack -> target-architect`

### Phase exit criteria

- target stack choice is explicit, persisted, and ordered correctly in the flow

---

## Phase 6 — Target Architecture, Review, Lock, And Target Adapters

### Goal

Implement the future-state architecture and make target-side adapters explicit.

### Work

1. Add `adapters/target/python_backend.py`.
2. Add `adapters/target/react_frontend.py`.
3. Add `pipeline/target_architect.py`.
4. Generate a graph-shaped target architecture artifact from:
   - semantic lock
   - source-architecture lock
   - target stack choice
5. Render `.modernize/architecture/target-architecture.md` using deterministic templates plus Mermaid.
6. Add review and approval commands for target architecture.
7. Persist target-architecture review state in `.modernize/architecture/target-architecture-review.json`.
8. Add target-architecture lock support.
9. Ensure the target architecture artifact explicitly records which target adapters are in play.

### Suggested target adapter API

```python
class TargetAdapter:
    name: str
    role: str
    version: str

    def architecture_conventions(self) -> dict: ...
    def generate_files(self, target_architecture: dict, service_name: str) -> list[GeneratedFile]: ...
```

### Files likely added/changed

- [python_backend.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/target/python_backend.py)
- [react_frontend.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/target/react_frontend.py)
- [target_architect.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/target_architect.py)
- [target_architecture.md.j2](/Users/koustubh/Documents/modern-app/app/modernize_demo/templates/target_architecture.md.j2)
- [locker.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/locker.py)
- [modernize.py](/Users/koustubh/Documents/modern-app/app/modernize.py)

### Unit tests

- target architecture artifact contains services, APIs, and ownership boundaries
- target architecture rendering includes the expected sections
- target architecture lock requires approval
- target adapters expose conventions as expected
- target architecture review-state artifact is updated correctly on approval

### End-to-end test

- `... -> lock source-architecture -> choose-target-stack -> target-architect -> approve target-architecture -> lock target-architecture`

### Phase exit criteria

- target architecture is fully represented as artifact + document + reviewed lockable stage

---

## Phase 7 — Generation Of Runnable Python + React Output

### Goal

Generate a small but runnable target application from locked artifacts.

### Work

1. Update `pipeline/generator.py` to require:
   - semantic lock
   - source-architecture lock
   - target-architecture lock
2. Use target-side adapters to generate:
   - Python backend files
   - React frontend files
3. Write generation metadata:
   - generated at
   - source lock references
   - target adapter versions
4. Generate to a stable output directory under `.modernize/services/<app-or-service>/`.
5. Make the generated output actually runnable, even if narrow.
6. Add a smoke-test path for the generated app:
   - backend app imports and starts cleanly
   - frontend build or component smoke check passes
   - one end-to-end verification scenario can hit the generated backend behavior

### Suggested runnable output

Backend:

- small Python HTTP app using the standard library
- 1-2 endpoints
- in-memory or fixture-backed behavior

Frontend:

- small React app or React page served by the backend
- one flow that talks to the backend

Prefer the simplest runtime with the least operational friction.

### Files likely touched

- [generator.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/generator.py)
- target adapter modules

### Unit tests

- generation is blocked when locks are missing
- target adapters produce expected file sets
- generation metadata includes lock references

### End-to-end test

- full pipeline up to target-architecture lock, then generate
- assert generated backend/frontend files exist
- assert the generated backend starts or imports successfully
- assert the generated frontend passes a minimal smoke/build check

### Phase exit criteria

- generated app is present and runnable end-to-end

---

## Phase 8 — Verification, Audit Trail, And Minimal Invalidation

### Goal

Make the demo trustworthy by adding a concrete verification artifact, visible audit trail, and one stale-lock example.

### Work

1. Update `pipeline/verifier.py` to produce structured verification reports.
2. Add at least one or two verification scenarios tied to the generated app.
3. Ensure audit events are recorded for:
   - approval
   - lock creation
   - generation
   - verification
4. Add minimal invalidation logic in `core/invalidation.py`.
5. Detect when upstream source/config inputs changed after semantic lock or architecture locks were produced.
6. Block generation or mark the relevant stage stale until relock.

### Suggested invalidation rule set for demo

- if any source file hash changes after semantic lock:
  - semantic lock becomes stale
  - source architecture lock becomes stale
  - target architecture lock becomes stale
- if any discovered config or environment input hash changes after semantic lock:
  - semantic lock becomes stale
  - source architecture lock becomes stale
  - target architecture lock becomes stale
- if target architecture changes after target lock:
  - generation must be blocked until relock

Keep this minimal and explicit.

### Files likely added/changed

- [invalidation.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/invalidation.py)
- [verifier.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/verifier.py)
- [generator.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/pipeline/generator.py)
- [state.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/core/state.py)

### Unit tests

- stale-lock detection works for changed source hash
- stale-lock detection works for changed config/environment input hash
- generation refuses to run when locks are stale
- verification report shape is correct
- audit log receives expected events

### End-to-end test

- full happy-path pipeline to verification
- source change after semantic lock causes stale-lock behavior
- config change after semantic lock causes stale-lock behavior

### Phase exit criteria

- verification artifact exists
- audit trail exists
- minimal invalidation story is implemented and demoable

---

## 11. CLI Command Set To End Up With

The final CLI should include commands close to:

- `init`
- `choose-provider`
- `discover`
- `parse`
- `facts`
- `extract`
- `review semantics`
- `approve semantics`
- `lock semantics`
- `source-architect`
- `review source-architecture`
- `approve source-architecture`
- `lock source-architecture`
- `choose-target-stack`
- `target-architect`
- `review target-architecture`
- `approve target-architecture`
- `lock target-architecture`
- `generate`
- `verify`
- `status`

Command naming can be slightly different, but the stage separation must remain.

---

## 12. Status Output Expectations

Update `status` so it shows:

- current stage
- per-stage status
- lock presence
- stale/valid state
- generated services/apps
- verification verdicts

This status screen will be useful in the demo and during testing.

---

## 13. Documentation To Update Along The Way

Update these as implementation progresses:

- [README.md](/Users/koustubh/Documents/modern-app/app/README.md)
- sample command list
- test instructions
- expected artifact directory structure
- how to run generated Python + React output

Do not wait until the end to document basic run instructions.

---

## 14. Recommended Order Of File Changes

Use this order unless implementation reveals a strong reason not to:

1. `core/state.py`
2. `core/audit.py`
3. `core/hashing.py`
4. `modernize.py`
5. discovery + parser + facts
6. AI providers + extractor + reviewer + semantic lock
7. source architecture + templates + source lock
8. target stack choice
9. target adapters + target architecture + target lock
10. generator
11. verifier
12. invalidation
13. status polishing
14. README polishing

---

## 15. Phase Completion Checklist

At the end of every phase, verify:

- the phase code is complete
- new tests are added, not just existing tests reused
- `python -m unittest discover -s tests` is green
- there is at least one end-to-end test for the phase
- artifact paths are consistent with the plan
- audit logging still works
- CLI help remains understandable

If a phase is only partially complete, do not start the next one.

---

## 16. Final Acceptance Criteria

The implementation is complete only if:

- the tool is Python-based end-to-end
- the pipeline ingests arbitrary small ColdFusion inputs
- AST, fact, semantic, architecture, lock, verification, and audit artifacts are all visible
- source-side and target-side adapters are explicit in both code and workflow
- AI providers are pluggable behind a common interface
- Gemini supports both API keys and Google ADC / Vertex AI
- semantic, source-architecture, and target-architecture locks are all enforced
- the generated Python + React output is runnable end-to-end
- a stale-lock scenario is demonstrable
- tests exist for each phase and the full happy path

---

## 17. Notes For The Implementing Agent

- Prefer evolving the current scaffold instead of rewriting it wholesale.
- Keep artifact schemas simple and explicit.
- Use templates for Markdown rendering.
- Keep Mermaid generation deterministic.
- If a full parser library becomes impractical, implement a narrow adapter honestly and keep the adapter boundary clean.
- Do not oversell AI in the code or docs. The trust model depends on clear locks and deterministic artifacts.
