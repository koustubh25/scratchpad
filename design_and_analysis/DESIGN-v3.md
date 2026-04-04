# Modernize — Advisory Agent Layer (v3)

> **This document extends [DESIGN-v2.md](./DESIGN-v2.md).** The deterministic AST-first pipeline, lock manager, semantic model, and 7 code-generation agents are unchanged. v3 adds an **advisory agent layer** — 6 specialized AI agents that wrap the deterministic core with quality assurance, risk analysis, and review intelligence at every stage.

---

## The Pitch: Deterministic Core + Intelligent Agent Layer

The v2 pipeline's strength is determinism: locked artifacts, checksummed approvals, reproducible outputs. That's the engineering story. The consulting story needs more.

**v3 framing:** Every stage where a senior consultant would look over your shoulder and say "wait, have you thought about..." — we've automated that. The deterministic core is the client's **guarantee**. The advisory agents are the **intelligence layer** that helps them understand what to approve, what to prioritize, and what to watch out for.

**Agent count:** 13 specialized AI agents total:
- **7 code-generation agents** (DB, UI, Logic, Auth, Form, Task, Email) — transform locked mappings into working code *(unchanged from v2)*
- **6 advisory agents** (Discovery, Review Prioritizer, Architecture Contradiction Detector, Migration Risk, Security Audit, Test Generation) — quality assurance at every pipeline stage *(new in v3)*

**The lock mechanism is the client's protection:** they approve every understanding before any code is generated. The advisory agents help them understand *what* to approve. The lock ensures no agent can change *what was approved*.

---

## Advisory Agent Guarantees

All 6 advisory agents follow these constraints:

1. **Write-isolated:** Advisory agents write only to `.modernize/agents/`. They never modify `.modernize/locked/`, `.modernize/semantics/`, `.modernize/ast/`, or `.modernize/services/`.
2. **Non-blocking:** The pipeline never waits on advisory agent output. They run in parallel with their host stage and surface results at the next human review checkpoint.
3. **Auditable:** Every advisory agent run is logged in `.modernize/audit/` — what it received, what it produced, which provider it used.
4. **Sanitized:** Advisory agents pass through the same sanitizer as code-generation agents. Trust level settings apply equally.
5. **Optional:** Any advisory agent can be disabled without affecting the pipeline. `modernize config agents --disable security-audit-agent`.

---

## Advisory Agent YAML Convention

Advisory agents follow the same YAML format as v1/v2 code-generation agents, with two new fields:

```yaml
name: discovery-agent
advisory: true                    # distinguishes from code-gen agents
appliesTo: ["semantic-model"]
stages: [extract]
outputPath: ".modernize/agents/discovery-report.json"

systemPrompt: |
  ...

conventions: |
  ...

outputSchema:
  ...
```

The Core Engine enforces: agents with `advisory: true` can only write to `.modernize/agents/`. Clients can define custom advisory agents for their domain (e.g., an HIPAA-compliance audit agent for healthcare engagements) using the same YAML format.

---

## What Is an Agent?

In this framework, an **agent is a YAML configuration file** — not a running process, not an MCP tool, not a subprocess, not a microservice. It contains three things:

1. A **system prompt** — domain expertise framing for the AI ("You are an expert in ColdFusion database access patterns...")
2. **Conventions** — language-specific idioms and patterns as context
3. An **output schema** — the exact JSON shape the AI must return

The `modernize` CLI is the only running process. When a pipeline stage needs AI, it:
1. Reads the relevant agent YAML
2. Assembles a context packet (system prompt + conventions + task instruction + input data + output schema)
3. Sends the packet to the configured AI provider via the Core Engine
4. Validates the response against the output schema
5. Writes the result to the appropriate output path

There is no agent runtime, no long-running processes, no inter-agent communication. Agents are stateless configuration that the CLI consumes.

### Code-Generation Agents vs Advisory Agents

| | Code-Generation Agents | Advisory Agents |
|---|---|---|
| **Count** | 7 (DB, UI, Logic, Auth, Form, Task, Email) | 6 (Discovery, Review Prioritizer, Arch Contradiction, Migration Risk, Security Audit, Test Generation) |
| **YAML field** | `advisory: false` (default) | `advisory: true` |
| **Output location** | `.modernize/services/` (committed code) | `.modernize/agents/` (reports only) |
| **Pipeline effect** | Produces artifacts that move to next stage | Produces reports for human review |
| **Can be disabled** | No — required for code generation | Yes — pipeline works without them |

### Agent Naming: Component-Type, Not Language

The 7 code-generation agents are **component-type-specific**, not target-language-specific:

- `cf-query-agent` knows what a ColdFusion query *is* — SQL dialects, parameterization, ORM patterns (source expertise from the source adapter)
- The Go target adapter provides Go conventions — sqlc, Chi router patterns, error handling (target expertise)
- The React target adapter provides React conventions — hooks, JSX, component patterns

**Same agent + different target adapter = different output language.** The `cf-` prefix comes from the ColdFusion source adapter that declares the agent, not from any target language. A Java source adapter would declare `java-query-agent` with Java-specific source conventions, but the same Go/React target adapters apply.

---

## AI Provider Flexibility

Clients have different AI environments. The framework is **provider-agnostic** — the Core Engine calls an abstract AI Provider Interface with three methods:

| Method | Purpose |
|--------|---------|
| `sendPrompt(context)` | Send assembled context packet, receive structured response |
| `getModelInfo()` | Get model capabilities (max tokens, supports JSON mode, etc.) |
| `estimateTokens(text)` | Estimate token count for context budget management |

All agents — both code-generation and advisory — use this same interface. Configuration:

```bash
modernize init ./app --provider azure-openai --model gpt-4o
modernize init ./app --provider claude --model claude-sonnet-4-6
modernize init ./app --provider bedrock --model anthropic.claude-3
modernize init ./app --provider vertex --model gemini-2.5-pro
modernize init ./app --provider ollama --model llama3    # self-hosted
```

No agent has a direct dependency on any specific AI provider. If a client has Azure OpenAI but not Claude, the pipeline works identically — only the provider adapter changes.

---

## AI Reliability

Advisory agents are **reliable, not deterministic** — and the design is honest about this distinction.

**What "deterministic" means in this pipeline:** Steps 1 (Parse AST), 4 (Review), 5a (Lock Semantics), 5g-h (Lock Architecture), and 8 (Deploy) produce identical output given identical input, every time. No AI involved.

**What "reliable" means for AI-assisted steps:** The same input to an AI agent may produce slightly different output on different runs. We don't pretend otherwise. Instead, we make AI output **reliable enough to be useful** and **reviewable enough to catch errors**:

| Mechanism | How It Works |
|-----------|-------------|
| **Structured I/O** | Agents receive JSON semantic models, not free text. Same structured input → much more consistent output |
| **Schema validation** | Every response is validated against the agent's `outputSchema`. Malformed responses are rejected and retried (up to 3 attempts) |
| **Confidence scoring** | Every AI-generated field carries a confidence score (0-100). Fields below threshold are flagged for human review |
| **Human review gates** | No AI output is committed to locked artifacts without human approval. The lock step is the hard guarantee |
| **Idempotency checks** | Optional: run an agent twice on the same input. If results diverge beyond a threshold, flag as low-confidence |
| **Source tagging** | AI-generated fields are tagged `"source": "ai"` so reviewers know exactly what to scrutinize vs what was deterministically extracted |

**The honest framing:** AI stages are reliable. The lock step is what makes the overall pipeline deterministic — it freezes the human-approved understanding regardless of how it was produced. The advisory agents help humans make better approval decisions, but the human is always the final authority.

---

## Agent Runtime: How Agents Execute

### No Framework

This design does **not** use LangGraph, CrewAI, AutoGen, or any agent orchestration framework. The agents here are stateless, single-turn AI calls with structured I/O. There is no multi-turn reasoning, no agent-to-agent communication, no dynamic tool use, no autonomous decision-making. The `modernize` CLI is the orchestrator — it decides what runs when.

Adding a framework would mean:
- Extra dependency clients must install and support
- Framework-specific abstractions obscuring simple request/response calls
- Lock-in to a specific framework's graph model
- Harder debugging (framework stack traces vs simple API call logs)

The orchestration is a linear pipeline with human gates. That's ~200 lines of Python, not a framework.

### Execution Model

When the CLI reaches a step that requires AI:

```
1. CLI identifies which agent(s) to invoke for this step
2. For each module (parallelized):
   a. Load agent YAML (system prompt, conventions, output schema)
   b. Load input data (AST nodes, semantic model, locked mappings — depends on step)
   c. Core Engine: sanitize input → chunk if needed → assemble context packet
   d. Core Engine: send to AI provider → validate response against output schema
   e. If validation fails: retry up to 3 times with error feedback in prompt
   f. If still fails: mark module as "agent-failed", continue with others
   g. Write output to appropriate path
3. Aggregate results across modules
4. Surface results at next human review checkpoint
```

### Parallelization

Agent calls are embarrassingly parallel at the module level. 200 modules × 1 agent = 200 independent API calls. The CLI runs N calls concurrently (configurable, default: 5 to respect provider rate limits).

```bash
# Control parallelism
modernize config concurrency --max-parallel 10

# Provider-specific rate limits
modernize config provider --rate-limit 60/min
```

Advisory agents run in parallel with their host stage's code-generation agents — they share the same input but write to different output paths, so there's no contention.

### Error Handling

| Failure | Behavior |
|---------|----------|
| Schema validation failure | Retry up to 3 times. Append validation error to prompt on retry. |
| Provider timeout | Kill request. Retry with smaller chunk if input was large. |
| Provider rate limit (429) | Exponential backoff with jitter. Queue continues. |
| Provider error (500) | Retry up to 3 times. If persistent, mark module as failed. |
| Agent produces low-confidence output | Accept but flag. Surface at review checkpoint. |
| Module marked as "agent-failed" | Pipeline continues with other modules. Failed modules listed in `modernize status`. Human can retry individually: `modernize retry extract UserService`. |

No silent failures. Every agent call — success or failure — is logged in `.modernize/audit/`.

### Why Not a Framework (Decision Record)

We evaluated LangGraph, CrewAI, and AutoGen against our requirements:

| Requirement | Our Design | Framework Approach |
|-------------|-----------|-------------------|
| Stateless single-turn calls | Python `async` + provider SDK | Graph nodes with state management overhead |
| Structured I/O with schema validation | JSON schema validation in Core Engine | Framework-specific output parsers |
| Human review gates | CLI pauses, waits for human input | Framework "human-in-the-loop" abstractions |
| Provider-agnostic | Abstract interface, 3 methods | Framework's provider abstractions (often opinionated) |
| Audit logging | Write to `.modernize/audit/` on every call | Framework-specific logging (varies in quality) |
| Debuggability | Read the context packet, read the response, done | Navigate framework internals to find the actual API call |
| Client deployment | `pip install modernize` | `pip install modernize` + framework + framework dependencies |

The frameworks solve coordination of multi-step, multi-agent autonomous workflows. Our agents don't coordinate — they execute independently, produce structured output, and a human decides what happens next. The CLI *is* the orchestrator.

**If this changes** — if we later need agents that call other agents, use tools dynamically, or make multi-step autonomous decisions — we should revisit. But the current design explicitly avoids autonomous agent behavior in favor of human-gated, auditable, single-turn calls.

---

## Agent 1: Discovery Agent

**Replaces:** The unnamed "minimal AI" in v2 Step 2 (Extract Semantics)
**Stage:** Step 2 — runs after deterministic AST extraction
**AI Usage:** Moderate (expanded from v2's "Minimal")

### What Changed from v2

v2 Step 2 uses AI only for "business rule naming + implicit rules." The Discovery Agent names that capability and expands it:

| v2 (unnamed) | v3 (Discovery Agent) |
|---|---|
| Business rule naming | Business rule naming |
| Implicit rule inference | Implicit rule inference |
| — | Cross-module pattern detection |
| — | Dead code identification |
| — | Gap flagging for reviewer attention |

### What It Receives

- All semantic model files from deterministic extraction (`.modernize/semantics/*.semantic.json`)
- Cross-module dependency graph (`.modernize/semantics/cross-module.json`)
- AST node list (`.modernize/ast/*.ast.json`)

### What It Produces

`.modernize/agents/discovery-report.json`:

```json
{
  "businessRules": [
    {
      "module": "UserService",
      "function": "authenticate",
      "name": "User Authentication",
      "description": "Validates credentials against stored hash and establishes session",
      "confidence": 92
    }
  ],
  "crossModulePatterns": [
    {
      "patternName": "Duplicate Auth Check",
      "modules": ["UserService", "AdminService", "APIGateway"],
      "description": "Three modules independently verify session.userId before proceeding",
      "recommendation": "Consolidate into shared auth middleware in target architecture"
    }
  ],
  "implicitRules": [
    {
      "module": "UserService",
      "function": "authenticate",
      "ruleName": "Account Lockout Policy",
      "description": "After 3 failed attempts, locks account for 30 minutes",
      "astEvidence": "Conditional node in try/catch block, line 45-52",
      "confidence": 74
    }
  ],
  "deadCode": [
    {
      "module": "UserService",
      "function": "legacyPasswordReset",
      "reason": "No callers in call graph — replaced by resetPasswordV2"
    }
  ],
  "gapFlags": [
    {
      "module": "ReportService",
      "function": "generateMonthly",
      "field": "businessRule",
      "suggestion": "Ask original developer: what business logic determines which records are included in the monthly report?"
    }
  ]
}
```

### How It Integrates

The discovery report feeds into Step 3 (Generate Docs) — the `Items Needing Review` section in review documents is populated from `gapFlags` and low-confidence `implicitRules`. The report is also consumed by the Review Prioritizer Agent.

### YAML Definition

```yaml
name: discovery-agent
advisory: true
appliesTo: ["semantic-model", "ast-nodes"]
stages: [extract]
outputPath: ".modernize/agents/discovery-report.json"

systemPrompt: |
  You are an expert in legacy application analysis. You receive a structured
  semantic model extracted from ColdFusion source code. Your job is to:
  1. Name business rules — what does each function accomplish in business terms?
  2. Identify cross-module patterns — duplicate logic, shared patterns, copy-paste code
  3. Flag implicit business rules — logic hidden in conditionals that static analysis missed
  4. Identify dead code — functions with no inbound calls in the call graph
  5. Flag gaps — functions where the semantic model has empty or placeholder fields

conventions: |
  - ColdFusion scope prefixes: session.*, application.*, variables.*, this.*
  - CFCs with init() method follow the constructor pattern
  - <cfinclude> creates implicit dependencies not visible in function calls
  - Query-of-queries (QoQ) operates on in-memory result sets, not database tables

outputSchema:
  businessRules:
    - module: string
      function: string
      name: string
      description: string
      confidence: number
  crossModulePatterns:
    - patternName: string
      modules: string[]
      description: string
      recommendation: string
  implicitRules:
    - module: string
      function: string
      ruleName: string
      description: string
      astEvidence: string
      confidence: number
  deadCode:
    - module: string
      function: string
      reason: string
  gapFlags:
    - module: string
      function: string
      field: string
      suggestion: string
```

---

## Agent 2: Review Prioritizer Agent

**Stage:** Step 3 — runs after doc generation, before human review
**AI Usage:** Minimal

### The Problem It Solves

A large ColdFusion app might have 200+ modules producing 200+ review documents. Original developers can't review everything with equal attention. The Review Prioritizer ranks items by migration risk so reviewers focus on what matters most.

> This also addresses the v2 TODO (Step 3): *"Static reports may be hard for developers to review — they have to mentally map extracted semantics back to code they wrote years ago."* The prioritized checklist tells reviewers exactly where to start and what question to answer for each item.

### What It Receives

- All semantic model files
- Discovery Agent output (gap flags, implicit rules, confidence scores)
- Cross-module dependency graph

### What It Produces

`.modernize/agents/review-checklist.json`:

```json
{
  "checklist": [
    {
      "rank": 1,
      "riskLevel": "CRITICAL",
      "module": "UserService",
      "function": "authenticate",
      "field": "implicitRule: Account Lockout Policy",
      "currentValue": "After 3 failed attempts, locks account for 30 minutes",
      "reviewPrompt": "Does this function actually lock accounts after failed attempts? The parser found this in a try/catch block — confirm the lockout logic and threshold.",
      "riskReason": "AI-inferred implicit rule (confidence: 74%) + writes to session scope + called by 12 other modules"
    },
    {
      "rank": 2,
      "riskLevel": "HIGH",
      "module": "ReportService",
      "function": "generateMonthly",
      "field": "businessRule",
      "currentValue": "(empty — gap flag)",
      "reviewPrompt": "What business logic determines which records are included in the monthly report?",
      "riskReason": "Empty business rule extraction — semantic model has no description for this function's purpose"
    }
  ],
  "summary": {
    "totalItems": 47,
    "criticalCount": 3,
    "highCount": 11,
    "mediumCount": 18,
    "lowCount": 15,
    "estimatedReviewMinutes": 240
  }
}
```

### Risk Ranking Factors

| Factor | Effect |
|--------|--------|
| AI confidence below 80% | HIGH minimum |
| Implicit rule flagged by Discovery Agent | HIGH minimum |
| Function writes to shared state (session/application scope) | Escalate one level |
| Function called by 5+ other modules (high fan-in) | Escalate one level |
| Gap flag (empty semantic field) | HIGH minimum |
| Dead code | LOW (but included — developer should confirm before migration) |

### CLI Integration

```bash
# Shows prioritized checklist summary first, then full review
modernize review semantics

# Shows only CRITICAL and HIGH items
modernize review semantics --prioritized

# Full checklist output
modernize agents review-checklist
```

---

## Agent 3: Architecture Contradiction Detector

**Stage:** Step 5e — runs after target architecture is designed (v2 Step 5d), before architecture review (v2 Step 5e). See DESIGN-v2.md for the full architecture stage breakdown.
**AI Usage:** Advisory (light)

### The Problem It Solves

The Architect Module (Step 5d) proposes service group boundaries. But ColdFusion monoliths often have deeply entangled data access — modules that look independent actually share tables, session state, or implicit transactions. The contradiction detector compares proposed boundaries against the locked semantic model to catch cuts that will break at runtime.

### What It Receives

- Proposed architecture decisions from Step 5d
- Locked semantic model (`.modernize/locked/semantic-lock.json`)
- Cross-module dependency graph

### Contradiction Types

| Type | What It Detects | Example |
|------|----------------|---------|
| **Shared-table violation** | Two proposed services both write to the same table | UserService and AuditService both write to `users` table — splitting them requires deciding table ownership |
| **Tight-coupling cut** | Proposed boundary cuts through heavily-used call paths | UserService calls SessionService 14 times — splitting creates 14 synchronous cross-service calls |
| **Session-state split** | Session-writing module and session-reading module placed in different services | UserService writes `session.userId`, ReportService reads it — splitting requires shared session or token-based auth |
| **Transaction boundary violation** | Modules participating in the same implicit transaction placed in different services | OrderService and InventoryService both write in the same `<cftransaction>` block |

### What It Produces

`.modernize/agents/arch-contradictions.json`:

```json
{
  "contradictions": [
    {
      "type": "shared-table",
      "severity": "BLOCKING",
      "services": ["users-service", "audit-service"],
      "description": "Both services write to the 'users' table. users-service owns authentication columns; audit-service writes to last_login and login_count columns.",
      "evidence": {
        "modules": ["UserService", "AuditLogger"],
        "semanticFact": "UserService: UPDATE users SET password_hash; AuditLogger: UPDATE users SET last_login, login_attempts"
      },
      "resolution": {
        "option": "ownership",
        "description": "Split the users table: auth columns owned by users-service, audit columns moved to a new audit_log table owned by audit-service"
      }
    }
  ],
  "summary": {
    "blockingCount": 1,
    "warningCount": 3,
    "approvalRecommendation": "revise-and-resubmit"
  }
}
```

### CLI Integration

```bash
# Shows contradiction summary at top of architecture review
modernize review architect

# Direct access to contradiction report
modernize agents arch-contradictions
```

If BLOCKING contradictions exist, `modernize review architect` prints a warning that must be acknowledged before approving.

---

## Agent 4: Migration Risk Agent

**Stage:** Between Steps 5d (architecture locked) and 6 (generate code)
**AI Usage:** Advisory (moderate)

### The Problem It Solves

Before generating a single line of code, the client wants to know: which service groups are safe to migrate first, and which are risky? The Migration Risk Agent produces a client-facing risk dashboard — a consulting deliverable that justifies the migration sequence.

### What It Receives

- Architecture lock (service groups + module composition)
- Semantic lock (per-module complexity, table counts, dependency counts, state usage)
- Discovery report (dead code counts, gap flags per module)

### Risk Dimensions (per service group)

| Dimension | What It Measures |
|-----------|-----------------|
| **Complexity** | Aggregate cyclomatic complexity of member modules |
| **Data sensitivity** | Count of tables with PII-pattern columns (email, password, ssn, dob) |
| **Dependency count** | Inbound + outbound cross-service dependencies |
| **State entanglement** | Session/application scope writes requiring JWT migration |
| **Test coverage gap** | Functions with no existing test references (inferred from AST) |
| **Discovery gaps** | Count of gap flags from Discovery Agent in this service group |

### What It Produces

`.modernize/agents/migration-risk-dashboard.json` and `.modernize/agents/migration-risk-dashboard.md`:

```json
{
  "serviceGroups": [
    {
      "name": "users-service",
      "riskScore": 62,
      "riskLevel": "MEDIUM",
      "dimensions": {
        "complexity": 45,
        "dataSensitivity": 85,
        "dependencyCount": 30,
        "stateEntanglement": 70,
        "testCoverageGap": 55,
        "discoveryGaps": 40
      },
      "topRisks": [
        "High data sensitivity — users table contains email, password_hash, role columns",
        "Session-to-JWT migration — 6 session scope writes across 3 modules",
        "Test gap — authenticate() and updateProfile() have no existing test references"
      ],
      "mitigations": [
        "Generate security audit agent report before code review",
        "Prioritize manual test creation for auth flows before cutover",
        "Engage original developer for session migration validation"
      ]
    }
  ],
  "recommendedSequence": ["static-content-service", "reports-service", "users-service", "admin-service"],
  "executiveSummary": "4 service groups identified. static-content-service and reports-service are low-risk leaf services — recommended as migration starters. users-service has medium risk due to auth complexity and PII data. admin-service should migrate last due to cross-service dependencies on 3 other services."
}
```

### CLI Integration

```bash
# Run risk assessment (after architecture lock)
modernize agents risk-dashboard

# Shows risk summary before generation
modernize generate users-service
# → "Migration Risk: MEDIUM (62/100) — 3 top risks identified. Run 'modernize agents risk-dashboard' for details."

# Risk dashboard in status output
modernize status
```

### Consulting Value

The `.md` version of the risk dashboard is a direct client deliverable. It demonstrates that the system understands their codebase deeply enough to quantify migration risk before a single line of new code is written.

---

## Agent 5: Security Audit Agent

**Stage:** Post-Step 6 — runs after code generation, before code review
**AI Usage:** Advisory (moderate)

### The Problem It Solves

ColdFusion → Go/React migration has known security drift patterns. Session-based auth becomes JWT. `<cfqueryparam>` becomes `sqlc` parameterized queries. `<cfoutput>` with `HTMLEditFormat()` becomes React's JSX escaping. The security audit agent verifies that the generated code preserves the security properties declared in the locked semantic model.

### What It Checks

| Check | What It Verifies | Locked Model Reference |
|-------|-----------------|----------------------|
| **Auth pattern drift** | JWT claim set covers all session scope writes | `stateWrites` in semantic model |
| **SQL parameterization** | Generated queries use parameterized bindings | `"parameterized": true` per query in semantic model |
| **OWASP Top 10** | No XSS, injection, broken auth, sensitive data exposure | Target conventions + locked data access patterns |
| **Missing auth middleware** | Functions requiring auth have middleware applied | `access: public/private` + auth patterns in semantic model |
| **Data exposure** | API responses don't leak PII fields not in the original return type | `outputs` in semantic model vs generated response struct |

### What It Receives

- Generated code for a service group (`.modernize/services/<service>/`)
- Locked semantic model (auth patterns, data access, state writes)
- Target adapter conventions

### What It Produces

`.modernize/agents/<service>/security-audit.json` and `.modernize/agents/<service>/security-audit.md`:

```json
{
  "findings": [
    {
      "severity": "HIGH",
      "category": "auth-drift",
      "file": "services/users-service/backend/handlers/user_handler.go",
      "lineRange": "45-52",
      "description": "Login handler returns user.role in JWT claims, but locked semantic model also records session.userPermissions — not mapped to any JWT claim",
      "semanticEvidence": "Locked stateWrites: [session.userId, session.userRole, session.userPermissions]",
      "remediation": "Add userPermissions to JWT claims or document why it was intentionally dropped"
    },
    {
      "severity": "MEDIUM",
      "category": "data-exposure",
      "file": "services/users-service/backend/handlers/user_handler.go",
      "lineRange": "78-85",
      "description": "GetUserById returns password_hash in the User struct — locked model output specifies only {id, email, role}",
      "semanticEvidence": "Locked outputs: {type: struct, keys: [id, email, role]}",
      "remediation": "Remove password_hash from the response DTO"
    }
  ],
  "summary": {
    "criticalCount": 0,
    "highCount": 1,
    "mediumCount": 1,
    "lowCount": 3,
    "passRate": 89,
    "approvalRecommendation": "approve-with-fixes"
  }
}
```

### CLI Integration

```bash
# Run security audit for a service group
modernize agents security-audit users-service

# Code review shows security summary first
modernize review generate users-service
# → "Security Audit: 1 HIGH, 1 MEDIUM finding. Review .modernize/agents/users-service/security-audit.md"
```

---

## Agent 6: Test Generation Agent

**Stage:** Step 7 — runs alongside the existing Verifier Module
**AI Usage:** Moderate (expanded from v2's "Light")

### The Problem It Solves

Consulting clients want tests as a deliverable — not just "we verified it works" but an actual test suite they own going forward. The Test Generation Agent produces two categories of tests from the locked semantic model, giving the client a test suite derived from their own approved business rules.

### Two Test Categories

| Category | Source | Purpose |
|----------|--------|---------|
| **Behavioral equivalence tests** | Locked function signatures (inputs → outputs) | Assert new code produces same outputs as the locked mapping specifies |
| **Business rule unit tests** | Locked business rules + control flow | One test per business rule, named after the rule. Control flow facts become test cases |

### Example Output

From the locked semantic model for `UserService.authenticate`:

**Go test (`_test.go`):**
```go
func TestUserAuthentication_ValidCredentials(t *testing.T) {
    // From locked mapping: authenticate(email, password) → {id, email, role}
    // Business rule: "Validates credentials against stored hash and establishes session"
}

func TestUserAuthentication_InvalidEmail_ReturnsError(t *testing.T) {
    // From locked control flow: "no user found → throw InvalidCredentials"
}

func TestUserAuthentication_WrongPassword_ReturnsError(t *testing.T) {
    // From locked control flow: "password mismatch → throw InvalidCredentials"
}

func TestUserAuthentication_LocksAfter3Failures(t *testing.T) {
    // From locked implicit rule (discovered by Discovery Agent):
    // "After 3 failed attempts, locks account for 30 minutes"
}
```

### What It Receives

- Locked semantic model (function signatures, business rules, control flow)
- Generated code (to reference actual function names and types)
- Behavioral recording data from Verifier Module (if available)

### What It Produces

- `.modernize/agents/<service>/test-suite-supplement_test.go` (Go tests)
- `.modernize/agents/<service>/test-suite-supplement.spec.ts` (React/TypeScript tests)
- `.modernize/agents/<service>/test-manifest.json` (coverage summary)

```json
{
  "testFiles": [
    {
      "path": ".modernize/agents/users-service/test-suite-supplement_test.go",
      "language": "go",
      "testCount": 24,
      "categories": {
        "equivalenceTests": 14,
        "businessRuleTests": 10
      }
    }
  ],
  "coverage": {
    "businessRulesWithTests": 18,
    "totalBusinessRules": 22,
    "coveragePercent": 82
  }
}
```

### How Tests Are Delivered

Tests are placed in `.modernize/agents/`, not committed to the generated service code directly. The developer reviews and moves them into the service's test suite. This preserves human ownership — the agent generates, the human curates.

### CLI Integration

```bash
# Generate supplemental tests
modernize agents generate-tests users-service

# View test coverage against business rules
modernize agents test-coverage users-service
```

---

## Updated Pipeline with Advisory Agents

The base pipeline is defined in DESIGN-v2.md (including the architecture stage split into 5b/5c/5d). v3 adds advisory agent steps:

```
Step 1:  Parse AST                    (deterministic)
Step 2:  Extract Semantics            (+ Discovery Agent — moderate AI)
Step 3:  Generate Docs                (+ Review Prioritizer Agent — minimal AI)
Step 4:  Review with Original Devs    (human-only, aided by prioritized checklist)
Step 5a: Lock Semantics               (deterministic freeze)
Step 5b: Analyze Existing Architecture(AI — moderate)
Step 5c: Choose Target Stack          (HUMAN DECISION — no AI)
Step 5d: Design Target Architecture   (AI — moderate)
      +: Check Contradictions         (Arch Contradiction Agent — advisory)
Step 5e: Review Target Architecture   (human-only, aided by contradiction report)
Step 5f: Lock Architecture            (deterministic freeze)
Step 5g: Final Lock                   (semantics + architecture frozen together)
Pre-6:   Risk Assessment              (Migration Risk Agent — advisory)
Step 6:  Generate Code                (7 code-gen agents — heavy AI)
Post-6:  Security Audit               (Security Audit Agent — advisory)
Step 6r: Code Review                  (human-only, aided by security report)
Step 7:  Verify                       (+ Test Generation Agent — moderate AI)
Step 8:  Deploy                       (deterministic)
```

---

## Updated AI Usage Summary

This table shows v3 advisory agent additions on top of the v2 base pipeline (see DESIGN-v2.md for the full AI usage table):

| Step | v2 AI Usage | v3 Addition | Advisory Agent |
|------|------------|-------------|---------------|
| 2. Extract Semantics | Minimal | Expanded to moderate | `discovery-agent` |
| 3. Generate Docs | Minimal | + review prioritization | `review-prioritizer-agent` |
| After 5d. Design Target Arch | — | Contradiction detection | `arch-contradiction-agent` |
| Pre-6. (new) | — | Risk scoring | `migration-risk-agent` |
| Post-6. (new) | — | Security audit | `security-audit-agent` |
| 7. Verify | Light | Expanded to moderate | `test-generation-agent` |

Advisory agents wrap every AI-assisted step, producing separately-auditable outputs that never modify locked artifacts. Code generation agents (Step 6) are where AI output is committed; everything else is input enrichment and quality assurance.

---

## State Directory Addition

Add to the existing `.modernize/` structure from v2:

```
.modernize/
├── ...                             # (all v2 directories unchanged)
│
├── agents/                         # Advisory agent outputs (v3)
│   ├── discovery-report.json       # Discovery Agent output
│   ├── review-checklist.json       # Review Prioritizer output
│   ├── arch-contradictions.json    # Architecture Contradiction Detector output
│   ├── migration-risk-dashboard.json
│   ├── migration-risk-dashboard.md # Client deliverable
│   └── <service>/                  # Per-service agent outputs
│       ├── security-audit.json
│       ├── security-audit.md
│       ├── test-suite-supplement_test.go
│       ├── test-suite-supplement.spec.ts
│       └── test-manifest.json
```

---

## CLI Additions

```bash
# Advisory agent commands (all read-only — produce reports, never modify pipeline state)
# Architecture stage commands (architect --existing, config target-stack, architect --target) are in DESIGN-v2.md

# Discovery report
modernize agents discovery-report

# Prioritized review checklist
modernize agents review-checklist
modernize review semantics --prioritized    # shortcut: shows CRITICAL + HIGH only

# Architecture contradiction report
modernize agents arch-contradictions

# Migration risk dashboard
modernize agents risk-dashboard

# Security audit (per service)
modernize agents security-audit <service>

# Test generation (per service)
modernize agents generate-tests <service>
modernize agents test-coverage <service>

# Disable/enable advisory agents
modernize config agents --disable <agent-name>
modernize config agents --enable <agent-name>

# List all agents and their status
modernize agents list
```

---

## Implementation Phase Additions

Advisory agents are distributed across the existing v2 phases:

| v2 Phase | Advisory Agents Added |
|----------|---------------------|
| **Phase 2** (Parser + Extractor + ColdFusion Adapter) | `discovery-agent`, `review-prioritizer-agent` |
| **Phase 3** (Lock Manager + Architect Module) | `arch-contradiction-agent`, `migration-risk-agent` |
| **Phase 5** (Verifier Module) | `security-audit-agent`, `test-generation-agent` |

Each advisory agent is implemented after its host pipeline stage is working — the agent depends on the stage's output artifacts existing.
