# Demo Plan: ColdFusion to Python + React

## Goal

Build a small but credible modernization demo that proves three things:

1. A slice of real ColdFusion source can be understood in a structured way.
2. That understanding can be reviewed and locked before generation.
3. A working Python + React target application can be produced from those locked artifacts.

This is not a full production implementation of the entire framework. It is a focused demo that shows the core modernization concept in a way that is believable to engineers and useful to directors.

## Audience

- Engineers
- One technical director
- One more business-facing but still somewhat technical director

The demo should therefore emphasize:

- disciplined stages, not black-box magic
- reviewability and governance
- visible lock/freeze points
- real source input and real generated output
- architecture comparison against a developer-reviewed source architecture

## Demo Scope

Use the provided ColdFusion files as the source input.

The demo should operate on a narrow but meaningful slice of the application, not necessarily every file end-to-end. The slice should be large enough to show:

- request handling
- data access
- business logic
- some shared dependencies
- a small frontend surface

The target stack for the demo will be:

- Python backend
- React frontend

The demo should also make adapter boundaries explicit:

- source-side adapters interpret legacy source conventions and parsing outputs
- target-side adapters apply Python and React generation conventions

The demo tool itself should also be implemented in Python.

That means the orchestration CLI, pipeline stages, artifact handling, locking, and demo workflow logic should all be built in Python, even though the generated target application is a separate Python + React output.

## Chosen Demo Slice

The demo should not attempt to modernize the entire ColdFusion input set uniformly.

Instead, it should focus on a selected slice that is rich enough to demonstrate the workflow clearly.

That slice should ideally include:

- one request or entry path
- one or more business rules
- one or more database interactions
- one shared dependency or coupling point
- one frontend-facing interaction that can be surfaced in React

Because the actual ColdFusion files are not yet available, the implementation should stay generic and should not hardcode assumptions about one named slice.

The demo should therefore be built so that:

- it can ingest an arbitrary small ColdFusion subset
- the pipeline stages operate on discovered inputs rather than preselected files
- the implementation does not depend on one fixed example slice being present during development

## Core Story To Demonstrate

The demo should tell this story clearly:

1. Start with real ColdFusion files.
2. Capture source, config, and environment inputs that influence behavior.
3. Use source-side adapters plus existing parsing libraries to extract deterministic structure and useful facts.
4. Produce visible AST and fact artifacts before interpretation.
5. Derive semantic meaning and allow review.
6. Lock approved semantics.
7. Derive source architecture.
8. Review and lock the source architecture.
9. Compare derived source architecture with the architecture reviewed by the original developer team.
10. Design target architecture for Python + React.
11. Lock the target architecture.
12. Use target-side adapters to generate working target code.
13. Run lightweight verification against expected behavior.

## Determinism Boundaries

The demo should make the determinism boundaries explicit.

These parts should be shown as deterministic:

- source/config discovery
- parsing and AST persistence
- fact extraction
- artifact writing
- review state recording
- lock creation
- state transitions

These parts can be AI-assisted but should still be shown as structured and auditable:

- semantic derivation
- architecture reasoning
- target code generation

This distinction is important to the credibility of the demo.

## What Should Be Real

These parts should be implemented as real demo capabilities, not just described:

- CLI-driven stage progression
- `.modernize/` state and artifact directories
- source intake using the provided ColdFusion files
- source/config/environment capture for the selected slice
- source-side adapter behavior
- target-side adapter behavior
- deterministic artifact generation for parse/facts where feasible
- fact artifact generation
- semantic review flow
- semantic review documents that are easy for humans to read
- semantic lock
- source architecture artifact
- source architecture review/approval state
- source architecture lock
- target architecture artifact
- target architecture review/approval state
- target architecture lock
- generation gated by locks
- working Python + React output for the chosen demo slice
- basic verification output
- lightweight audit/log output
- minimal stale-lock detection when upstream artifacts change

## What Can Stay Lightweight

These parts can be simplified for the demo:

- parser completeness across all ColdFusion patterns
- AI sophistication
- verification breadth
- full regeneration conflict handling
- full cutover implementation
- generalized adapter marketplace

They should still be represented honestly, but they do not need to be fully production-grade in the demo.

## Parsing Strategy

The demo should not attempt to build a parser from scratch.

Instead, it should rely on existing parsing libraries and practical extraction techniques where possible, for example:

- Tree-sitter or similar parser libraries
- source-language heuristics for unsupported constructs
- narrow extraction focused on the selected demo slice

The goal of the demo is not to prove a complete ColdFusion parser. The goal is to prove that the modernization workflow can operate on structured source understanding and turn it into reviewed, locked, and generated outputs.

## Demo Non-Goals

The demo is not intended to be:

- a full production implementation of the modernization platform
- a complete ColdFusion parser
- a generalized multi-language adapter marketplace
- a fully automated cutover system
- a full verification framework for every edge case
- a complete migration of the entire provided source estate

These limits should remain explicit so the implementation stays focused on the core demonstration value.

## Why The Lock Manager Matters

The lock manager should be a visible part of the demo, not hidden infrastructure.

It should show:

- approved artifacts being frozen
- who approved them
- when they were approved
- checksums or fingerprints
- refusal to proceed when required locks are missing
- warning or refusal when upstream artifacts have changed and locks are stale

This is one of the most important differentiators in the demo because it makes the process feel governed rather than improvisational.

## Audit And Replayability

The demo does not need a full audit subsystem, but it should include a visible audit trail artifact.

At minimum, it should record:

- major stage transitions
- approvals
- lock creation
- generation events
- verification events

This helps explain lineage and makes the pipeline feel inspectable rather than opaque.

## Minimal Invalidation Story

The demo should include one small but explicit invalidation example.

For example:

- a source file or config input changes after semantics are locked
- the system detects the upstream change
- downstream generation is blocked or marked stale until relock

This does not need to become a full invalidation engine, but it should demonstrate that locks are not decorative.

## Source Architecture Comparison

One of the strongest demo moments should be a comparison between:

- the source architecture derived by the pipeline
- the source architecture reviewed by the original developer team

This does not need to be framed as “perfect match or failure.”

Instead, it should show:

- where the derived architecture aligns well
- where it is less complete or less certain
- how review improves confidence

This is likely to be one of the most persuasive parts of the demo for both engineers and leadership.

For the demo, this comparison should be treated as a validation aid, not as a required automated pipeline stage.

That means:

- the pipeline-derived source architecture is generated by the demo workflow
- the developer-reviewed source architecture comes from the original team
- the comparison between them can be manual or semi-manual

The purpose of the comparison is to show alignment, gaps, and confidence, not to claim that the framework automatically judges itself against a human-reviewed reference architecture.

## Architecture Document Templates

The demo should generate architecture documents from structured artifacts using controlled templates.

These documents should not be hand-written from scratch and should not rely entirely on freeform AI prose generation.

For the demo, use deterministic Markdown templates for:

- semantic review index document
- semantic review module documents
- source architecture document
- target architecture document
- architecture comparison document

The documents should also include Mermaid diagrams generated from the structured architecture artifacts.

This is an important part of the demo because it shows that reviewed architecture artifacts can be turned into readable engineering documents with diagrams.

For semantic review specifically, do not generate one giant Markdown file. Generate:

- one semantic review index document
- one semantic review document per module

This scales much better than a single global semantic dump and matches the long-term review model more closely.

### Source Architecture Document Template

The source architecture document should include:

1. Scope
2. System Summary
3. Modules and Responsibilities
4. Dependencies
5. Data and State
6. Hotspots and Risks
7. Review Notes
8. Lock Metadata

### Target Architecture Document Template

The target architecture document should include:

1. Scope
2. Target Stack
3. Service / Component Design
4. API Contracts
5. Data Ownership and State Mapping
6. Generation Boundaries
7. Risks / Review Notes
8. Lock Metadata

### Architecture Comparison Document Template

The comparison document should include:

1. Scope Compared
2. Major Alignments
3. Major Differences
4. Confidence / Gaps
5. Reviewer Notes

For the demo, the comparison document can be assembled manually or semi-manually using the generated source architecture document and the developer-reviewed architecture as inputs.

## Document Generation Policy

The demo should use a hybrid document-generation approach.

The main structure of the document should be deterministic and artifact-driven.

These parts should be generated deterministically from structured artifacts:

- section structure
- scope and module/service listings
- dependency and data/state sections
- lock metadata
- Mermaid diagrams

These parts may be AI-assisted if useful:

- short summary paragraphs
- hotspot and risk narrative
- migration rationale text

The important constraint is that AI should not be allowed to invent the core architecture structure independently of the approved artifacts.

## Required Inputs

The implementation phase should assume the following inputs are required:

- the ColdFusion source files that will later be provided for the demo
- any important config or environment inputs relevant to that slice
- the developer-reviewed source architecture reference in Markdown form
- target stack conventions for Python backend and React frontend
- a small set of expected behaviors or scenarios for verification

If any of these are missing, the implementation plan should call that out early.

## Implementation Constraint

The demo tool should be written in Python.

This should be treated as a firm implementation constraint for the next planning phase.

In practice, that means:

- the CLI should be Python-based
- the pipeline and lock manager should be Python-based
- artifact generation and state management should be Python-based
- any supporting comparison or document-generation utilities should be Python-based unless there is a very strong reason otherwise

## Deliverables

The demo should ideally include:

- a runnable CLI flow
- a `.modernize/` artifact directory
- real sample ColdFusion inputs
- source/config discovery output
- source-side adapter stage
- AST artifacts
- fact artifacts
- semantic artifacts
- locked semantic artifacts
- source architecture artifact
- locked source architecture artifact
- generated source architecture document
- developer-reviewed source architecture reference
- architecture comparison output
- target architecture artifact
- locked architecture artifact
- generated target architecture document
- target-side adapter stage
- generated Python backend code
- generated React frontend code
- verification report
- audit trail artifact
- stale-lock or invalidation example

## Live Demo Emphasis

During the demo, the emphasis should be:

- “we can understand the legacy system in a reviewable way”
- “we can freeze approved understanding before code generation”
- “we can compare our architecture understanding against developer-reviewed truth”
- “we can generate a working Python + React slice from locked inputs”

The emphasis should not be:

- “the AI can autonomously modernize everything”

That would be a weaker and less defensible story.

## Implementation Direction

The existing `mock_tool` directory should be the starting point.

The next implementation phase should focus on:

1. upgrading the mock pipeline so it can ingest the real ColdFusion demo files
2. wiring in source-side parsing/extraction using existing libraries instead of writing a parser from scratch
3. improving the lock manager so it is visibly meaningful in the demo
4. adding source architecture review, lock, and comparison support
5. making source-side and target-side adapters explicit in the workflow
6. generating a small but working Python + React target slice
7. producing a clean verification artifact

## Additional Implementation Decisions

The implementation plan should assume the following:

- the demo should support a generic ColdFusion input set rather than one fixed hardcoded slice
- the original-team architecture reference will be provided as Markdown
- the generated target application should be runnable end-to-end, even if it is small
- the review flow only needs a small interactive correction capability, not a full review product

## High-Level Implementation Phases

The detailed implementation plan should likely break into phases like these:

1. Demo slice selection and input preparation
2. Source intake, parsing, and fact artifact generation
3. Semantic review and lock workflow
4. Source architecture generation, review, lock, and comparison support
5. Target architecture generation and lock workflow
6. Python + React generation for the chosen slice
7. Verification, audit artifacts, and demo packaging

These phases should guide the next planning document.

## Success Criteria

The demo is successful if the audience can see that:

- the process is staged and controlled
- locks are meaningful and enforceable
- architecture understanding is reviewable
- generated output is based on approved artifacts
- the Python + React target is not hand-waved but actually produced

## Acceptance Criteria

The implementation plan should treat the demo as done only if:

- a selected ColdFusion slice can be ingested and processed by the demo pipeline
- the demo produces visible AST, fact, semantic, and architecture artifacts
- semantic, source architecture, and target architecture locks are all visible and enforced
- source-side and target-side adapters are visible in the workflow
- source architecture can be compared against the developer-reviewed reference
- the demo generates a working Python + React output for the chosen slice
- verification produces a concrete artifact for that generated output
- the `.modernize/` directory tells a coherent artifact story
