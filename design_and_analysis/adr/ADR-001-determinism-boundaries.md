# ADR-001: Determinism Boundaries

## Context

The design uses both deterministic processing and AI-assisted reasoning. Earlier documents risked overstating determinism by describing the overall platform as deterministic without clearly separating reproducible mechanics from non-deterministic inference.

## Decision

Use "deterministic" only for parsing, artifact persistence, state transitions, locking, invalidation, and replayable non-AI processing. Treat AI-assisted semantics, architecture suggestions, and code generation as structured, auditable, and human-governed, but not deterministic.

Human-approved locks are the boundary that turns reviewed non-deterministic output into deterministic downstream input.

## Consequences

- marketing and technical docs must avoid claiming deterministic AI interpretation
- review and lock stages become central to the value proposition
- run-to-run variance in AI outputs is acceptable before lock, but not after lock

## Rejected Alternatives

- Claim end-to-end determinism for the whole pipeline
- Avoid the word "deterministic" entirely
