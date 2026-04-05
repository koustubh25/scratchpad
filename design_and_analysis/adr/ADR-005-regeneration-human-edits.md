# ADR-005: Regeneration Policy for Human-Edited Generated Code

## Context

Generated code will often be reviewed and edited by engineers. Subsequent regeneration creates a safety problem: the system must not silently erase human work, but it also cannot assume generated files are forever immutable.

## Decision

Persist baseline generation metadata for generated outputs and detect human modifications before regeneration. When edits are detected, regeneration requires an explicit decision per affected output: overwrite, merge, or skip and mark manually maintained.

Silent overwrite is prohibited.

## Consequences

- generation metadata becomes part of the required artifact model
- regeneration UX must surface changed files clearly
- some outputs will leave machine-managed mode over time

## Rejected Alternatives

- Always overwrite generated files
- Forbid human edits to generated outputs
