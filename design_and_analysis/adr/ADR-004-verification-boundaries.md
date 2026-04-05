# ADR-004: Verification Boundaries and Behavioral Equivalence

## Context

Verification is critical, but exact behavioral equivalence is not always realistic for legacy-to-modern migrations. Some drift is acceptable, while some is a release blocker. The design needs explicit boundaries.

## Decision

Verification will prove conformance to locked semantics and scenario-based behavioral equivalence for defined high-risk flows. It will classify drift as acceptable or failing using explicit rules. Verification will not claim universal correctness outside reviewed semantics and covered scenarios.

## Consequences

- verification scenarios and replay data become first-class artifacts
- business sign-off is needed for acceptable-drift rules
- database migration correctness still requires separate controls

## Rejected Alternatives

- Claim full equivalence without scenario boundaries
- Reduce verification to unit tests generated from the target code only
