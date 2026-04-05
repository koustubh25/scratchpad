# Plan: Canonical Design Document + Supporting ADRs

## Summary

Create a new canonical technical design document that replaces the current version-fragmented story with one builder-focused source of truth. Base it primarily on the architecture in `DESIGN-v2.md`, keep only the advisory-layer content from `DESIGN-v3.md` that materially improves the core workflow, and pull the highest-priority risks from `RISKS.md` directly into subsystem design constraints.

The goal of the new document is to make the system implementable and reviewable without cross-reading old versions. It must define what is deterministic, what is AI-assisted, where humans intervene, how artifacts are locked, how regeneration works, and how failure/recovery behaves at scale.

## Key Changes

### 1. Create one canonical design document

Draft a new document in `design_and_analysis` as the single source of truth for technical implementation.

Document structure:

1. Problem and design principles
2. System guarantees and non-guarantees
3. Determinism boundaries
4. End-to-end pipeline
5. Core data model and artifacts
6. Semantic extraction architecture
7. Review and lock workflow
8. Architecture design and code generation workflow
9. Verification strategy
10. Incremental execution and invalidation model
11. Operational controls: cost, concurrency, audit, recovery
12. Risk-driven constraints by subsystem
13. MVP scope and explicit non-goals

Required framing decisions:

- State clearly that parsing, artifact management, locks, state transitions, and replayability are deterministic.
- State clearly that AI-assisted extraction, architectural reasoning, and code generation are structured and auditable, but not deterministic.
- Define the lock step as the mechanism that converts reviewed AI-assisted output into deterministic downstream input.

### 2. Make the top risks first-class design constraints

Embed these directly in the canonical doc, not as an appendix-only concern:

- Parser/AST coverage risk
- Semantic extraction bottleneck
- Review throughput and reviewer conflict
- Verification incompleteness
- Database/config/environment dependency risk
- Incremental invalidation and stale artifact risk

For each major subsystem, include:

- failure mode
- detection signal
- mitigation approach
- explicit non-goal or limitation

### 3. Keep v3 advisory agents, but demote them to optional support

Retain advisory agents only as optional, non-blocking review accelerators. The canonical doc should say:

- they do not participate in locked state transitions
- they cannot modify locked artifacts or generated code
- the system remains functional without them
- they are secondary to the extraction-lock-verify core

Include only the agents that materially improve review and risk surfacing. Avoid expanding the main architecture around them.

### 4. Add a small ADR set for the hardest decisions

Create short ADRs alongside the canonical doc for decisions likely to be revisited or challenged:

ADR list:

- Determinism boundaries and honest terminology
- AST/fact/semantic layered extraction model
- Human review + lock as governance mechanism
- Verification strategy and behavioral equivalence limits
- Regeneration policy when generated code has human edits

Each ADR should contain:

- context
- decision
- consequences
- rejected alternatives

### 5. Reposition old documents

Keep existing docs as historical references, but make the new canonical doc the only current implementation reference.

Expected repo-facing outcome:

- old docs remain for history
- new canonical doc explicitly supersedes them
- ADRs hold the sharp controversial decisions that should not be buried in the main narrative

## Public Interfaces / Types / Artifacts To Clarify In The New Doc

The new document should explicitly define these artifacts and interfaces at a behavior level:

- AST artifact: structured parse output, parse status, adapter version, source hash
- Fact extraction artifact: deterministic extracted facts from AST, with confidence only where heuristics apply
- Semantic model artifact: reviewed higher-level meaning with `source`, confidence, and correction provenance
- Lock artifacts: semantic lock and architecture lock, checksum-based, versioned, and review-attributed
- Regeneration metadata: baseline generation fingerprint, human-edit detection status, merge/skip/overwrite policy
- Verification artifacts: replay results, drift classification, failure capture, and config snapshot linkage
- Invalidation rules: what becomes stale when source changes, adapter version changes, config changes, or reviewer corrections land

## Test / Acceptance Criteria For The Document

The new document is complete only if it lets an implementer answer these without consulting prior versions:

- What are the exact deterministic vs AI-assisted stages?
- What is the minimum artifact chain from source file to generated service?
- How does semantic extraction progress from facts to meaning?
- How are low-confidence items surfaced and corrected?
- What invalidates locked or generated artifacts?
- How are human edits to generated code handled safely?
- What does verification prove, and what does it explicitly not prove?
- What happens when parsing is partial, a module fails extraction, or an advisory agent fails?
- What is in scope for the MVP, and what is deferred?

Document quality checks:

- no references to "see prior version for core behavior"
- no unresolved contradiction between commercial language and technical guarantees
- no core risk mentioned without an architectural response

## Assumptions And Defaults

- `DESIGN-v2.md` is the technical base.
- `DESIGN-v3.md` contributes optional advisory-agent behavior only.
- `DESIGN-v4.md` is not the technical base; its useful commercial framing can be reused later in a separate buyer-facing document.
- The new canonical document is builder-first, not buyer-first.
- Risk treatment should be inline in the design, with a separate operational risk register remaining optional.
- The immediate deliverable is the document set and structure, not implementation changes.
