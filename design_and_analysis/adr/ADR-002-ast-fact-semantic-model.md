# ADR-002: AST -> Facts -> Semantics Layering

## Context

The hardest technical problem is not code generation. It is producing stable, reviewable understanding from messy legacy systems. Mixing parsing, behavior extraction, and business interpretation in one stage makes the pipeline brittle and hard to validate.

## Decision

Use a strict layered model:

`Source -> AST -> Facts -> Semantics -> Review -> Lock`

Facts remain deterministic and evidence-based. Semantics may use heuristics and AI, but every inferred field must point back to supporting facts or AST evidence.

## Consequences

- parser quality and fact extraction become explicit foundation work
- review becomes more targeted because meaning is separated from raw structure
- partial understanding is possible without blocking the whole pipeline

## Rejected Alternatives

- Let AI interpret raw source directly at multiple stages
- Collapse facts and semantics into one artifact
