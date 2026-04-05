# ADR-003: Review and Lock Governance

## Context

Legacy modernization has high consequence for incorrect interpretation. AI confidence scores help prioritize review, but they do not provide an acceptable governance boundary for production migration decisions.

## Decision

Use structured human review followed by immutable lock artifacts. Only reviewed artifacts can be locked. Downstream architecture and generation must read from locks, not from mutable draft artifacts.

## Consequences

- the system is slower than a fully autonomous generator, but materially safer
- stale lock handling becomes required infrastructure
- reviewer attribution and conflict resolution must be built into the workflow

## Rejected Alternatives

- Auto-approve AI output based only on confidence
- Allow generation directly from draft semantic artifacts
