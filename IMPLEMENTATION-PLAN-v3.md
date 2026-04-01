# Implementation Plan — Modernize CLI (v3 — Advisory Agent Layer)

> **Audience**: An AI coding assistant (Sonnet 4.5 or equivalent) that will implement this plan step by step.
> **Source of truth**: `DESIGN-v3.md` in this repo. This plan translates that design into exact code specifications.
> **Prerequisite**: `IMPLEMENTATION-PLAN-v2.md` must be implemented first. This plan extends the v2 codebase — it does NOT duplicate v2 code. Every file here either creates a new file or adds to an existing v2 file.
> **Key constraint**: Advisory agents are YAML config files consumed by the CLI. There is no agent runtime, no framework, no long-running processes.

---

## Table of Contents

1. [Relationship to v2](#1-relationship-to-v2)
2. [Directory Structure Additions](#2-directory-structure-additions)
3. [Dependencies (No New Ones)](#3-dependencies-no-new-ones)
4. [Data Models (New Types)](#4-data-models-new-types)
5. [Advisory Agent Infrastructure](#5-advisory-agent-infrastructure)
6. [Agent 1: Discovery Agent](#6-agent-1-discovery-agent)
7. [Agent 2: Review Prioritizer Agent](#7-agent-2-review-prioritizer-agent)
8. [Agent 3: Architecture Contradiction Detector](#8-agent-3-architecture-contradiction-detector)
9. [Agent 4: Migration Risk Agent](#9-agent-4-migration-risk-agent)
10. [Agent 5: Security Audit Agent](#10-agent-5-security-audit-agent)
11. [Agent 6: Test Generation Agent](#11-agent-6-test-generation-agent)
12. [Pipeline Integration Points](#12-pipeline-integration-points)
13. [CLI Additions](#13-cli-additions)
14. [Testing Strategy](#14-testing-strategy)
15. [Implementation Order](#15-implementation-order)

---

## 1. Relationship to v2

v3 is a **layer on top of v2**. The deterministic pipeline, lock manager, code-generation agents, and all 28 risk mitigations are unchanged. v3 adds:

- 6 advisory agent YAML definitions
- Infrastructure to run advisory agents in parallel with pipeline stages
- Output models for each advisory agent
- CLI commands to view advisory agent reports
- Integration hooks in existing pipeline modules (parser, extractor, architect, generator, verifier)

**What v3 does NOT change:**
- No modifications to `core/models.py` v2 dataclasses (new types go in a new section)
- No modifications to the lock manager, checkpoint, audit, or cost tracking
- No modifications to code-generation agent YAML files
- No modifications to provider adapters

**What v3 modifies (adds to, does not replace):**
- `core/models.py` — new dataclasses appended at the end
- `agents/loader.py` — advisory agent loading (already supports `advisory: true` field from v2)
- `agents/registry.py` — filter by advisory vs code-gen
- `pipeline/extractor.py` — hook to run Discovery Agent after extraction
- `pipeline/documenter.py` — hook to run Review Prioritizer after doc generation
- `pipeline/architect.py` — hook to run Arch Contradiction Detector after Step 5d
- `pipeline/generator.py` — hook to run Security Audit after code generation
- `pipeline/verifier.py` — hook to run Test Generation alongside verification
- `modernize.py` — new CLI commands under `agents` subgroup

---

## 2. Directory Structure Additions

Add these files to the existing `app/` tree from v2:

```
app/
├── ...                                 # (all v2 files unchanged)
│
├── advisory/                           # Advisory agent execution layer (NEW)
│   ├── __init__.py
│   ├── runner.py                       # Run advisory agents (parallel, non-blocking)
│   ├── discovery.py                    # Discovery Agent logic
│   ├── review_prioritizer.py           # Review Prioritizer Agent logic
│   ├── arch_contradiction.py           # Architecture Contradiction Detector logic
│   ├── migration_risk.py               # Migration Risk Agent logic
│   ├── security_audit.py               # Security Audit Agent logic
│   └── test_generation.py              # Test Generation Agent logic
│
├── advisory_agents/                    # Advisory agent YAML definitions (NEW)
│   ├── discovery-agent.yaml
│   ├── review-prioritizer-agent.yaml
│   ├── arch-contradiction-agent.yaml
│   ├── migration-risk-agent.yaml
│   ├── security-audit-agent.yaml
│   └── test-generation-agent.yaml
│
└── tests/
    ├── ...                             # (all v2 tests unchanged)
    ├── unit/
    │   ├── ...                         # (all v2 unit tests)
    │   ├── test_advisory_runner.py     # Advisory runner tests
    │   ├── test_discovery.py           # Discovery Agent output tests
    │   ├── test_review_prioritizer.py  # Review Prioritizer output tests
    │   ├── test_arch_contradiction.py  # Arch Contradiction output tests
    │   ├── test_migration_risk.py      # Migration Risk output tests
    │   ├── test_security_audit.py      # Security Audit output tests
    │   └── test_test_generation.py     # Test Generation output tests
    ├── integration/
    │   ├── ...                         # (all v2 integration tests)
    │   └── test_advisory_pipeline.py   # Advisory agents in pipeline flow
    └── fixtures/
        ├── ...                         # (all v2 fixtures)
        └── advisory/                   # Advisory agent test fixtures
            ├── sample_semantic_model.json
            ├── sample_cross_module.json
            ├── sample_discovery_report.json
            ├── sample_arch_decisions.json
            ├── sample_generated_code/
            │   ├── user_handler.go
            │   └── UserList.tsx
            └── sample_locked_semantics.json
```

### `.modernize/` State Directory Additions

v3 adds the `agents/` subdirectory inside `.modernize/`:

```
.modernize/
├── ...                                 # (all v2 directories unchanged)
│
└── agents/                             # Advisory agent outputs (NEW in v3)
    ├── discovery-report.json           # Discovery Agent output
    ├── review-checklist.json           # Review Prioritizer output
    ├── arch-contradictions.json        # Architecture Contradiction Detector output
    ├── migration-risk-dashboard.json   # Migration Risk Agent JSON output
    ├── migration-risk-dashboard.md     # Migration Risk Agent markdown (client deliverable)
    └── <service>/                      # Per-service advisory outputs
        ├── security-audit.json
        ├── security-audit.md
        ├── test-suite-supplement_test.go
        ├── test-suite-supplement.spec.ts
        └── test-manifest.json
```

**The `agents/` directory must be created by `ProjectState.init()`.** Add it to the directory creation list in `core/state.py`:

```python
# In ProjectState.init(), add to the mkdir list:
(self.modernize_dir / "agents").mkdir(parents=True, exist_ok=True)
```

---

## 3. Dependencies (No New Ones)

v3 requires NO new pip packages beyond what v2 already installs. Advisory agents use:
- `pyyaml` — load agent YAML definitions (already in v2)
- `jsonschema` — validate agent output (already in v2)
- AI provider SDKs — send prompts (already in v2)
- `rich` — display reports (already in v2)

---

## 4. Data Models (New Types)

File: `app/core/models.py` — append these after the existing v2 dataclasses.

### 4.1 Discovery Agent Output Models

```python
@dataclass
class DiscoveredBusinessRule:
    module: str
    function: str
    name: str
    description: str
    confidence: int                     # 0-100

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "function": self.function,
            "name": self.name,
            "description": self.description,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DiscoveredBusinessRule:
        return cls(
            module=data["module"],
            function=data["function"],
            name=data["name"],
            description=data["description"],
            confidence=data["confidence"],
        )

@dataclass
class CrossModulePattern:
    pattern_name: str
    modules: list[str]
    description: str
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "patternName": self.pattern_name,
            "modules": self.modules,
            "description": self.description,
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CrossModulePattern:
        return cls(
            pattern_name=data["patternName"],
            modules=data["modules"],
            description=data["description"],
            recommendation=data["recommendation"],
        )

@dataclass
class ImplicitRule:
    module: str
    function: str
    rule_name: str
    description: str
    ast_evidence: str
    confidence: int                     # 0-100

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "function": self.function,
            "ruleName": self.rule_name,
            "description": self.description,
            "astEvidence": self.ast_evidence,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ImplicitRule:
        return cls(
            module=data["module"],
            function=data["function"],
            rule_name=data["ruleName"],
            description=data["description"],
            ast_evidence=data["astEvidence"],
            confidence=data["confidence"],
        )

@dataclass
class DeadCodeEntry:
    module: str
    function: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "function": self.function,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DeadCodeEntry:
        return cls(
            module=data["module"],
            function=data["function"],
            reason=data["reason"],
        )

@dataclass
class GapFlag:
    module: str
    function: str
    field: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "function": self.function,
            "field": self.field,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GapFlag:
        return cls(
            module=data["module"],
            function=data["function"],
            field=data["field"],
            suggestion=data["suggestion"],
        )

@dataclass
class DiscoveryReport:
    business_rules: list[DiscoveredBusinessRule] = field(default_factory=list)
    cross_module_patterns: list[CrossModulePattern] = field(default_factory=list)
    implicit_rules: list[ImplicitRule] = field(default_factory=list)
    dead_code: list[DeadCodeEntry] = field(default_factory=list)
    gap_flags: list[GapFlag] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "businessRules": [r.to_dict() for r in self.business_rules],
            "crossModulePatterns": [p.to_dict() for p in self.cross_module_patterns],
            "implicitRules": [r.to_dict() for r in self.implicit_rules],
            "deadCode": [d.to_dict() for d in self.dead_code],
            "gapFlags": [g.to_dict() for g in self.gap_flags],
        }

    @classmethod
    def from_dict(cls, data: dict) -> DiscoveryReport:
        return cls(
            business_rules=[DiscoveredBusinessRule.from_dict(r) for r in data.get("businessRules", [])],
            cross_module_patterns=[CrossModulePattern.from_dict(p) for p in data.get("crossModulePatterns", [])],
            implicit_rules=[ImplicitRule.from_dict(r) for r in data.get("implicitRules", [])],
            dead_code=[DeadCodeEntry.from_dict(d) for d in data.get("deadCode", [])],
            gap_flags=[GapFlag.from_dict(g) for g in data.get("gapFlags", [])],
        )
```

### 4.2 Review Prioritizer Output Models

```python
@dataclass
class ReviewChecklistItem:
    rank: int
    risk_level: str                     # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    module: str
    function: str
    field: str
    current_value: str
    review_prompt: str
    risk_reason: str

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "riskLevel": self.risk_level,
            "module": self.module,
            "function": self.function,
            "field": self.field,
            "currentValue": self.current_value,
            "reviewPrompt": self.review_prompt,
            "riskReason": self.risk_reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReviewChecklistItem:
        return cls(
            rank=data["rank"],
            risk_level=data["riskLevel"],
            module=data["module"],
            function=data["function"],
            field=data["field"],
            current_value=data["currentValue"],
            review_prompt=data["reviewPrompt"],
            risk_reason=data["riskReason"],
        )

@dataclass
class ReviewChecklistSummary:
    total_items: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    estimated_review_minutes: int

    def to_dict(self) -> dict:
        return {
            "totalItems": self.total_items,
            "criticalCount": self.critical_count,
            "highCount": self.high_count,
            "mediumCount": self.medium_count,
            "lowCount": self.low_count,
            "estimatedReviewMinutes": self.estimated_review_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReviewChecklistSummary:
        return cls(
            total_items=data["totalItems"],
            critical_count=data["criticalCount"],
            high_count=data["highCount"],
            medium_count=data["mediumCount"],
            low_count=data["lowCount"],
            estimated_review_minutes=data["estimatedReviewMinutes"],
        )

@dataclass
class ReviewChecklist:
    checklist: list[ReviewChecklistItem] = field(default_factory=list)
    summary: ReviewChecklistSummary | None = None

    def to_dict(self) -> dict:
        return {
            "checklist": [item.to_dict() for item in self.checklist],
            "summary": self.summary.to_dict() if self.summary else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReviewChecklist:
        return cls(
            checklist=[ReviewChecklistItem.from_dict(item) for item in data.get("checklist", [])],
            summary=ReviewChecklistSummary.from_dict(data["summary"]) if data.get("summary") else None,
        )
```

### 4.3 Architecture Contradiction Models

```python
@dataclass
class ContradictionEvidence:
    modules: list[str]
    semantic_fact: str

    def to_dict(self) -> dict:
        return {
            "modules": self.modules,
            "semanticFact": self.semantic_fact,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ContradictionEvidence:
        return cls(
            modules=data["modules"],
            semantic_fact=data["semanticFact"],
        )

@dataclass
class ContradictionResolution:
    option: str                         # "ownership" | "merge" | "extract" | "defer"
    description: str

    def to_dict(self) -> dict:
        return {
            "option": self.option,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ContradictionResolution:
        return cls(
            option=data["option"],
            description=data["description"],
        )

@dataclass
class ArchContradiction:
    contradiction_type: str             # "shared-table" | "tight-coupling" | "session-state-split" | "transaction-boundary"
    severity: str                       # "BLOCKING" | "WARNING"
    services: list[str]
    description: str
    evidence: ContradictionEvidence
    resolution: ContradictionResolution

    def to_dict(self) -> dict:
        return {
            "type": self.contradiction_type,
            "severity": self.severity,
            "services": self.services,
            "description": self.description,
            "evidence": self.evidence.to_dict(),
            "resolution": self.resolution.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ArchContradiction:
        return cls(
            contradiction_type=data["type"],
            severity=data["severity"],
            services=data["services"],
            description=data["description"],
            evidence=ContradictionEvidence.from_dict(data["evidence"]),
            resolution=ContradictionResolution.from_dict(data["resolution"]),
        )

@dataclass
class ArchContradictionReport:
    contradictions: list[ArchContradiction] = field(default_factory=list)
    blocking_count: int = 0
    warning_count: int = 0
    approval_recommendation: str = "approve"  # "approve" | "revise-and-resubmit"

    def to_dict(self) -> dict:
        return {
            "contradictions": [c.to_dict() for c in self.contradictions],
            "summary": {
                "blockingCount": self.blocking_count,
                "warningCount": self.warning_count,
                "approvalRecommendation": self.approval_recommendation,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> ArchContradictionReport:
        summary = data.get("summary", {})
        return cls(
            contradictions=[ArchContradiction.from_dict(c) for c in data.get("contradictions", [])],
            blocking_count=summary.get("blockingCount", 0),
            warning_count=summary.get("warningCount", 0),
            approval_recommendation=summary.get("approvalRecommendation", "approve"),
        )
```

### 4.4 Migration Risk Models

```python
@dataclass
class RiskDimensions:
    complexity: int                     # 0-100
    data_sensitivity: int               # 0-100
    dependency_count: int               # 0-100
    state_entanglement: int             # 0-100
    test_coverage_gap: int              # 0-100
    discovery_gaps: int                 # 0-100

    def to_dict(self) -> dict:
        return {
            "complexity": self.complexity,
            "dataSensitivity": self.data_sensitivity,
            "dependencyCount": self.dependency_count,
            "stateEntanglement": self.state_entanglement,
            "testCoverageGap": self.test_coverage_gap,
            "discoveryGaps": self.discovery_gaps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RiskDimensions:
        return cls(
            complexity=data["complexity"],
            data_sensitivity=data["dataSensitivity"],
            dependency_count=data["dependencyCount"],
            state_entanglement=data["stateEntanglement"],
            test_coverage_gap=data["testCoverageGap"],
            discovery_gaps=data["discoveryGaps"],
        )

@dataclass
class ServiceGroupRisk:
    name: str
    risk_score: int                     # 0-100 (weighted average of dimensions)
    risk_level: str                     # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    dimensions: RiskDimensions
    top_risks: list[str]
    mitigations: list[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "riskScore": self.risk_score,
            "riskLevel": self.risk_level,
            "dimensions": self.dimensions.to_dict(),
            "topRisks": self.top_risks,
            "mitigations": self.mitigations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ServiceGroupRisk:
        return cls(
            name=data["name"],
            risk_score=data["riskScore"],
            risk_level=data["riskLevel"],
            dimensions=RiskDimensions.from_dict(data["dimensions"]),
            top_risks=data["topRisks"],
            mitigations=data["mitigations"],
        )

@dataclass
class MigrationRiskDashboard:
    service_groups: list[ServiceGroupRisk] = field(default_factory=list)
    recommended_sequence: list[str] = field(default_factory=list)
    executive_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "serviceGroups": [sg.to_dict() for sg in self.service_groups],
            "recommendedSequence": self.recommended_sequence,
            "executiveSummary": self.executive_summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MigrationRiskDashboard:
        return cls(
            service_groups=[ServiceGroupRisk.from_dict(sg) for sg in data.get("serviceGroups", [])],
            recommended_sequence=data.get("recommendedSequence", []),
            executive_summary=data.get("executiveSummary", ""),
        )
```

### 4.5 Security Audit Models

```python
@dataclass
class SecurityFinding:
    severity: str                       # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    category: str                       # "auth-drift" | "sql-injection" | "data-exposure" | "xss" | "missing-auth"
    file: str
    line_range: str                     # "45-52"
    description: str
    semantic_evidence: str
    remediation: str

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "lineRange": self.line_range,
            "description": self.description,
            "semanticEvidence": self.semantic_evidence,
            "remediation": self.remediation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SecurityFinding:
        return cls(
            severity=data["severity"],
            category=data["category"],
            file=data["file"],
            line_range=data["lineRange"],
            description=data["description"],
            semantic_evidence=data["semanticEvidence"],
            remediation=data["remediation"],
        )

@dataclass
class SecurityAuditReport:
    findings: list[SecurityFinding] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    pass_rate: int = 100                # Percentage of checks that passed
    approval_recommendation: str = "approve"  # "approve" | "approve-with-fixes" | "revise-and-resubmit"

    def to_dict(self) -> dict:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "summary": {
                "criticalCount": self.critical_count,
                "highCount": self.high_count,
                "mediumCount": self.medium_count,
                "lowCount": self.low_count,
                "passRate": self.pass_rate,
                "approvalRecommendation": self.approval_recommendation,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> SecurityAuditReport:
        summary = data.get("summary", {})
        return cls(
            findings=[SecurityFinding.from_dict(f) for f in data.get("findings", [])],
            critical_count=summary.get("criticalCount", 0),
            high_count=summary.get("highCount", 0),
            medium_count=summary.get("mediumCount", 0),
            low_count=summary.get("lowCount", 0),
            pass_rate=summary.get("passRate", 100),
            approval_recommendation=summary.get("approvalRecommendation", "approve"),
        )
```

### 4.6 Test Generation Models

```python
@dataclass
class GeneratedTestFile:
    path: str                           # Relative to .modernize/agents/<service>/
    language: str                       # "go" | "typescript"
    test_count: int
    equivalence_tests: int
    business_rule_tests: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "testCount": self.test_count,
            "categories": {
                "equivalenceTests": self.equivalence_tests,
                "businessRuleTests": self.business_rule_tests,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> GeneratedTestFile:
        categories = data.get("categories", {})
        return cls(
            path=data["path"],
            language=data["language"],
            test_count=data["testCount"],
            equivalence_tests=categories.get("equivalenceTests", 0),
            business_rule_tests=categories.get("businessRuleTests", 0),
        )

@dataclass
class TestCoverage:
    business_rules_with_tests: int
    total_business_rules: int
    coverage_percent: float

    def to_dict(self) -> dict:
        return {
            "businessRulesWithTests": self.business_rules_with_tests,
            "totalBusinessRules": self.total_business_rules,
            "coveragePercent": self.coverage_percent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TestCoverage:
        return cls(
            business_rules_with_tests=data["businessRulesWithTests"],
            total_business_rules=data["totalBusinessRules"],
            coverage_percent=data["coveragePercent"],
        )

@dataclass
class TestManifest:
    test_files: list[GeneratedTestFile] = field(default_factory=list)
    coverage: TestCoverage | None = None

    def to_dict(self) -> dict:
        return {
            "testFiles": [f.to_dict() for f in self.test_files],
            "coverage": self.coverage.to_dict() if self.coverage else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TestManifest:
        return cls(
            test_files=[GeneratedTestFile.from_dict(f) for f in data.get("testFiles", [])],
            coverage=TestCoverage.from_dict(data["coverage"]) if data.get("coverage") else None,
        )
```

### 4.7 Advisory Agent Config Model

```python
@dataclass
class AdvisoryAgentConfig:
    """Runtime configuration for which advisory agents are enabled."""
    enabled: dict[str, bool] = field(default_factory=lambda: {
        "discovery-agent": True,
        "review-prioritizer-agent": True,
        "arch-contradiction-agent": True,
        "migration-risk-agent": True,
        "security-audit-agent": True,
        "test-generation-agent": True,
    })

    def is_enabled(self, agent_name: str) -> bool:
        return self.enabled.get(agent_name, True)

    def disable(self, agent_name: str) -> None:
        self.enabled[agent_name] = False

    def enable(self, agent_name: str) -> None:
        self.enabled[agent_name] = True

    def to_dict(self) -> dict:
        return {"advisoryAgents": self.enabled}

    @classmethod
    def from_dict(cls, data: dict) -> AdvisoryAgentConfig:
        return cls(enabled=data.get("advisoryAgents", {}))
```

---

## 5. Advisory Agent Infrastructure

### 5.1 `advisory/runner.py` — Advisory Agent Runner

This is the core orchestrator for advisory agents. It loads agent YAML, assembles context, sends to the AI provider, validates the response, and writes the output.

```python
from __future__ import annotations

import json
import asyncio
from pathlib import Path
from datetime import datetime

from core import console
from core.state import ProjectState
from core.audit import AuditLogger
from core.cost import CostTracker
from core.sanitizer import Sanitizer
from core.context_assembler import ContextAssembler
from core.models import AdvisoryAgentConfig
from core.errors import ModernizeError, ProviderError
from core.utils import atomic_write_json
from core.schema_version import stamp
from agents.loader import load_agent
from providers import create_provider


class AdvisoryAgentRunner:
    """Runs advisory agents: load YAML → assemble context → call AI → validate → write output.

    Advisory agents follow the same execution model as code-gen agents but:
    1. Write only to .modernize/agents/ (never to locked/, semantics/, services/)
    2. Are non-blocking — pipeline continues regardless of advisory agent success/failure
    3. Can be disabled per agent via config
    """

    def __init__(self, state: ProjectState):
        self.state = state
        self.migration = state.load()
        self.provider = create_provider(self.migration["provider"],
                                        model=self.migration.get("model"))
        self.audit = AuditLogger(state.modernize_dir / "audit")
        self.cost = CostTracker(state.modernize_dir / "audit", self.migration)
        self.sanitizer = Sanitizer(trust_level=self.migration.get("trustLevel", "standard"))
        self.config = self._load_advisory_config()

    def _load_advisory_config(self) -> AdvisoryAgentConfig:
        """Load advisory agent enable/disable config from migration.json."""
        return AdvisoryAgentConfig.from_dict(self.migration)

    def is_enabled(self, agent_name: str) -> bool:
        """Check if an advisory agent is enabled."""
        return self.config.is_enabled(agent_name)

    def run_agent(self, agent_yaml_path: str, input_data: dict,
                  output_path: str, task_instruction: str) -> dict | None:
        """Run a single advisory agent.

        Args:
            agent_yaml_path: Path to the agent's YAML definition file.
            input_data: The structured data to feed the agent (semantic models, AST, etc).
            output_path: Where to write the output (relative to .modernize/).
            task_instruction: The specific task instruction for this invocation.

        Returns:
            The parsed JSON output from the agent, or None if the agent failed.

        Flow:
        1. Load agent YAML definition
        2. Check if agent is enabled — skip if disabled
        3. Verify agent has advisory: true — refuse to run code-gen agents
        4. Sanitize input data per trust level
        5. Assemble context packet: system prompt + conventions + task instruction + input data + output schema
        6. Send to AI provider
        7. Parse response as JSON
        8. Validate response against agent's outputSchema (jsonschema)
        9. If validation fails: retry up to 3 times with error feedback
        10. If still fails: log warning, return None (non-blocking)
        11. Stamp with schema version
        12. Write output to .modernize/agents/... (via atomic_write_json)
        13. Log to audit trail
        14. Track cost
        15. Return the parsed output
        """
        agent_def = load_agent(agent_yaml_path)

        # Safety check: only run advisory agents
        if not agent_def.advisory:
            console.print(f"[red]Refusing to run non-advisory agent: {agent_def.name}[/]")
            return None

        # Check if enabled
        if not self.is_enabled(agent_def.name):
            console.print(f"[dim]Skipping disabled agent: {agent_def.name}[/]")
            return None

        # Sanitize input
        sanitized_input, redacted = self.sanitizer.sanitize_dict(input_data)

        # Assemble context
        assembler = ContextAssembler()
        context = assembler.build(
            system_prompt=agent_def.system_prompt,
            conventions=agent_def.conventions,
            task_instruction=task_instruction,
            input_data=json.dumps(sanitized_input, indent=2, default=str),
            output_schema=agent_def.output_schema,
        )

        # Send to AI with retries
        max_retries = 3
        last_error = ""
        result = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Append validation error to prompt for retry
                    context_with_error = context + f"\n\nPREVIOUS ATTEMPT FAILED VALIDATION:\n{last_error}\nPlease fix the output."
                else:
                    context_with_error = context

                response = self.provider.send_prompt(
                    system=agent_def.system_prompt,
                    prompt=context_with_error,
                    output_format="json",
                )

                # Parse JSON
                result = json.loads(response.content)

                # Validate against schema
                import jsonschema
                jsonschema.validate(result, agent_def.output_schema)

                # Success — break retry loop
                break

            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {e}"
                console.print(f"[yellow]Agent {agent_def.name} attempt {attempt + 1}: {last_error}[/]")
            except jsonschema.ValidationError as e:
                last_error = f"Schema validation error: {e.message}"
                console.print(f"[yellow]Agent {agent_def.name} attempt {attempt + 1}: {last_error}[/]")
            except ProviderError as e:
                last_error = f"Provider error: {e}"
                console.print(f"[yellow]Agent {agent_def.name} attempt {attempt + 1}: {last_error}[/]")
                if not e.retryable:
                    break

        if result is None:
            console.print(f"[red]Agent {agent_def.name} failed after {max_retries} attempts. Skipping (non-blocking).[/]")
            self.audit.log(
                action="advisory_agent_failed",
                module=agent_def.name,
                actor=f"ai:{self.migration.get('model', 'unknown')}",
                details={"error": last_error, "attempts": max_retries},
            )
            return None

        # Stamp with schema version
        result = stamp(result)

        # Write output
        output_full_path = self.state.modernize_dir / output_path
        output_full_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(output_full_path, result)

        # Audit log
        self.audit.log_ai_call(
            stage=f"advisory:{agent_def.name}",
            module=agent_def.name,
            provider=self.migration["provider"],
            model=self.migration.get("model", "unknown"),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            duration_ms=response.duration_ms,
            redacted_fields=redacted,
        )

        # Cost tracking
        self.cost.record_call(response.input_tokens, response.output_tokens)

        console.print(f"[green]Advisory agent {agent_def.name} completed. Output: {output_path}[/]")
        return result

    def run_agents_parallel(self, agents: list[dict]) -> dict[str, dict | None]:
        """Run multiple advisory agents in parallel.

        Args:
            agents: list of dicts, each with keys:
                - yaml_path: str
                - input_data: dict
                - output_path: str
                - task_instruction: str

        Returns:
            dict mapping agent yaml filename → output (or None if failed)

        Implementation: Use asyncio.gather with ThreadPoolExecutor for parallel AI calls.
        Respect concurrency config from migration.json.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        max_parallel = self.migration.get("concurrency", {}).get("maxParallel", 5)
        results = {}

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {}
            for agent_spec in agents:
                future = executor.submit(
                    self.run_agent,
                    agent_spec["yaml_path"],
                    agent_spec["input_data"],
                    agent_spec["output_path"],
                    agent_spec["task_instruction"],
                )
                futures[future] = agent_spec["yaml_path"]

            for future in as_completed(futures):
                yaml_path = futures[future]
                agent_name = Path(yaml_path).stem
                try:
                    results[agent_name] = future.result()
                except Exception as e:
                    console.print(f"[red]Agent {agent_name} raised exception: {e}[/]")
                    results[agent_name] = None

        return results
```

### 5.2 Updates to `agents/loader.py`

The existing v2 `load_agent()` already supports the `advisory: true` YAML field via the `AgentDefinition` dataclass. No code changes needed — but verify that it loads the `stages` and `outputPath` fields from the YAML:

```python
# Existing in v2 — verify these lines exist in agents/loader.py:
def load_agent(yaml_path: str) -> AgentDefinition:
    """Load an agent definition from a YAML file."""
    import yaml
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    return AgentDefinition(
        name=data["name"],
        applies_to=data.get("appliesTo", []),
        system_prompt=data.get("systemPrompt", ""),
        conventions=data.get("conventions", ""),
        output_schema=data.get("outputSchema", {}),
        stages=data.get("stages", []),
        advisory=data.get("advisory", False),        # v3 field
    )
```

### 5.3 Updates to `agents/registry.py`

Add methods to filter advisory vs code-gen agents:

```python
# Add to existing AgentRegistry class:

def get_advisory_agents(self) -> list[AgentDefinition]:
    """Return all loaded advisory agents."""
    return [a for a in self._agents.values() if a.advisory]

def get_code_gen_agents(self) -> list[AgentDefinition]:
    """Return all loaded code-generation agents (non-advisory)."""
    return [a for a in self._agents.values() if not a.advisory]

def get_advisory_for_stage(self, stage: str) -> list[AgentDefinition]:
    """Return advisory agents that apply to a given pipeline stage.
    Checks the 'stages' field in the agent YAML."""
    return [a for a in self._agents.values()
            if a.advisory and stage in a.stages]
```

### 5.4 Updates to `core/state.py`

Add `agents/` to directory creation in `ProjectState.init()`:

```python
# In ProjectState.init(), add this line after the other mkdir calls:
(self.modernize_dir / "agents").mkdir(parents=True, exist_ok=True)
```

### 5.5 Updates to `migration.json` Schema

Add advisory agent config to the migration.json schema:

```json
{
  "...": "...existing v2 fields...",
  "advisoryAgents": {
    "discovery-agent": true,
    "review-prioritizer-agent": true,
    "arch-contradiction-agent": true,
    "migration-risk-agent": true,
    "security-audit-agent": true,
    "test-generation-agent": true
  }
}
```

---

## 6. Agent 1: Discovery Agent

### 6.1 YAML Definition

File: `app/advisory_agents/discovery-agent.yaml`

```yaml
name: discovery-agent
advisory: true
appliesTo: ["semantic-model", "ast-nodes"]
stages: [extract]
outputPath: ".modernize/agents/discovery-report.json"

systemPrompt: |
  You are an expert in legacy application analysis. You receive a structured
  semantic model extracted from ColdFusion source code, along with the raw AST.
  Your job is to:
  1. Name business rules — what does each function accomplish in business terms?
  2. Identify cross-module patterns — duplicate logic, shared patterns, copy-paste code
  3. Flag implicit business rules — logic hidden in conditionals that static analysis missed
  4. Identify dead code — functions with no inbound calls in the call graph
  5. Flag gaps — functions where the semantic model has empty or placeholder fields

  Guidelines:
  - Be conservative with confidence scores. Only score above 90 if the AST evidence
    is unambiguous.
  - For implicit rules, always cite the specific AST evidence (line numbers, node types).
  - For dead code, verify against the full call graph — a function with no callers
    in THIS codebase might still be called by external systems.
  - For cross-module patterns, focus on patterns that affect migration decisions
    (consolidation opportunities, shared middleware candidates).

conventions: |
  - ColdFusion scope prefixes: session.*, application.*, variables.*, this.*
  - CFCs with init() method follow the constructor pattern
  - <cfinclude> creates implicit dependencies not visible in function calls
  - Query-of-Queries (QoQ) operates on in-memory result sets, not database tables
  - <cfmodule> and <cfimport> create custom tag dependencies
  - Application.cfc lifecycle methods: onRequestStart, onApplicationStart, onSessionStart
  - <cflock> blocks indicate shared state access patterns

outputSchema:
  type: object
  required: [businessRules, crossModulePatterns, implicitRules, deadCode, gapFlags]
  properties:
    businessRules:
      type: array
      items:
        type: object
        required: [module, function, name, description, confidence]
        properties:
          module: {type: string}
          function: {type: string}
          name: {type: string}
          description: {type: string}
          confidence: {type: number, minimum: 0, maximum: 100}
    crossModulePatterns:
      type: array
      items:
        type: object
        required: [patternName, modules, description, recommendation]
        properties:
          patternName: {type: string}
          modules: {type: array, items: {type: string}}
          description: {type: string}
          recommendation: {type: string}
    implicitRules:
      type: array
      items:
        type: object
        required: [module, function, ruleName, description, astEvidence, confidence]
        properties:
          module: {type: string}
          function: {type: string}
          ruleName: {type: string}
          description: {type: string}
          astEvidence: {type: string}
          confidence: {type: number, minimum: 0, maximum: 100}
    deadCode:
      type: array
      items:
        type: object
        required: [module, function, reason]
        properties:
          module: {type: string}
          function: {type: string}
          reason: {type: string}
    gapFlags:
      type: array
      items:
        type: object
        required: [module, function, field, suggestion]
        properties:
          module: {type: string}
          function: {type: string}
          field: {type: string}
          suggestion: {type: string}
```

### 6.2 `advisory/discovery.py` — Discovery Agent Logic

```python
from __future__ import annotations

import json
from pathlib import Path

from core import console
from core.state import ProjectState
from core.models import DiscoveryReport
from advisory.runner import AdvisoryAgentRunner


AGENT_YAML = str(Path(__file__).parent.parent / "advisory_agents" / "discovery-agent.yaml")


def run_discovery(state: ProjectState) -> DiscoveryReport | None:
    """Run the Discovery Agent after semantic extraction.

    Reads:
    - All .modernize/semantics/*.semantic.json files
    - .modernize/semantics/cross-module.json
    - All .modernize/ast/*.ast.json files

    Writes:
    - .modernize/agents/discovery-report.json

    Returns:
        DiscoveryReport or None if agent failed/disabled.
    """
    runner = AdvisoryAgentRunner(state)

    if not runner.is_enabled("discovery-agent"):
        return None

    # Gather input data
    semantic_models = {}
    for fname in state.list_artifacts("semantics", ".semantic.json"):
        data = state.read_artifact("semantics", fname)
        if data:
            module_name = fname.replace(".semantic.json", "")
            semantic_models[module_name] = data

    cross_module = state.read_artifact("semantics", "cross-module.json") or {}

    ast_nodes = {}
    for fname in state.list_artifacts("ast", ".ast.json"):
        data = state.read_artifact("ast", fname)
        if data:
            module_name = fname.replace(".ast.json", "")
            ast_nodes[module_name] = data

    if not semantic_models:
        console.print("[yellow]Discovery Agent: No semantic models found. Skipping.[/]")
        return None

    # Build input data packet
    input_data = {
        "semanticModels": semantic_models,
        "crossModule": cross_module,
        "astNodes": ast_nodes,
    }

    task_instruction = """Analyze the semantic models and AST nodes provided.
For EACH function in EVERY module:
1. Generate a business rule name and description.
2. Check for implicit rules hidden in conditionals, try/catch blocks, and scope writes.
3. Check if this function has any callers in the call graph — if not, flag as dead code.
4. Check if any semantic model fields are empty or placeholder — flag as gaps.

After processing all functions, look across ALL modules for:
- Duplicate logic patterns (same SQL, same validation, same auth checks)
- Copy-paste patterns (similar function bodies across modules)
- Shared middleware candidates (same pre-processing in multiple modules)

Return the complete JSON output matching the output schema."""

    result = runner.run_agent(
        agent_yaml_path=AGENT_YAML,
        input_data=input_data,
        output_path="agents/discovery-report.json",
        task_instruction=task_instruction,
    )

    if result is None:
        return None

    return DiscoveryReport.from_dict(result)
```

---

## 7. Agent 2: Review Prioritizer Agent

### 7.1 YAML Definition

File: `app/advisory_agents/review-prioritizer-agent.yaml`

```yaml
name: review-prioritizer-agent
advisory: true
appliesTo: ["semantic-model"]
stages: [document]
outputPath: ".modernize/agents/review-checklist.json"

systemPrompt: |
  You are an expert at prioritizing code review tasks for legacy application migration.
  You receive semantic models, discovery agent output, and cross-module dependency data.
  Your job is to produce a ranked checklist of items that need human review, ordered by
  migration risk.

  Ranking rules (highest priority first):
  1. CRITICAL: AI confidence below 60%, OR implicit rules with confidence below 70%
     AND the function writes to shared state or handles auth
  2. HIGH: AI confidence below 80%, OR any gap flags, OR implicit rules flagged by
     Discovery Agent, OR function writes to session/application scope
  3. MEDIUM: Functions called by 5+ other modules (high fan-in), OR functions with
     complex control flow (3+ conditionals)
  4. LOW: Dead code confirmations, clean extractions with high confidence

  For each item, write a specific reviewPrompt — a question the original developer
  can answer. Not "review this function" but "Does this function actually lock
  accounts after 3 failed attempts?"

  Estimate review time: 5 min for LOW, 10 min for MEDIUM, 20 min for HIGH,
  30 min for CRITICAL items.

conventions: |
  - Focus review prompts on BUSINESS LOGIC, not implementation details
  - Use the original ColdFusion function names so developers can find the code
  - Reference specific line numbers from AST evidence when available
  - Group related items (same module, same table) together in the ranking

outputSchema:
  type: object
  required: [checklist, summary]
  properties:
    checklist:
      type: array
      items:
        type: object
        required: [rank, riskLevel, module, function, field, currentValue, reviewPrompt, riskReason]
        properties:
          rank: {type: integer}
          riskLevel: {type: string, enum: [CRITICAL, HIGH, MEDIUM, LOW]}
          module: {type: string}
          function: {type: string}
          field: {type: string}
          currentValue: {type: string}
          reviewPrompt: {type: string}
          riskReason: {type: string}
    summary:
      type: object
      required: [totalItems, criticalCount, highCount, mediumCount, lowCount, estimatedReviewMinutes]
      properties:
        totalItems: {type: integer}
        criticalCount: {type: integer}
        highCount: {type: integer}
        mediumCount: {type: integer}
        lowCount: {type: integer}
        estimatedReviewMinutes: {type: integer}
```

### 7.2 `advisory/review_prioritizer.py` — Review Prioritizer Logic

```python
from __future__ import annotations

import json
from pathlib import Path

from core import console
from core.state import ProjectState
from core.models import ReviewChecklist
from advisory.runner import AdvisoryAgentRunner


AGENT_YAML = str(Path(__file__).parent.parent / "advisory_agents" / "review-prioritizer-agent.yaml")


def run_review_prioritizer(state: ProjectState) -> ReviewChecklist | None:
    """Run the Review Prioritizer Agent after doc generation.

    Reads:
    - All .modernize/semantics/*.semantic.json files
    - .modernize/agents/discovery-report.json (if exists — Discovery Agent output)
    - .modernize/semantics/cross-module.json

    Writes:
    - .modernize/agents/review-checklist.json

    Returns:
        ReviewChecklist or None if agent failed/disabled.
    """
    runner = AdvisoryAgentRunner(state)

    if not runner.is_enabled("review-prioritizer-agent"):
        return None

    # Gather input data
    semantic_models = {}
    for fname in state.list_artifacts("semantics", ".semantic.json"):
        data = state.read_artifact("semantics", fname)
        if data:
            module_name = fname.replace(".semantic.json", "")
            semantic_models[module_name] = data

    cross_module = state.read_artifact("semantics", "cross-module.json") or {}

    # Discovery report is optional — agent works without it
    discovery_report = state.read_artifact("agents", "discovery-report.json")

    if not semantic_models:
        console.print("[yellow]Review Prioritizer: No semantic models found. Skipping.[/]")
        return None

    input_data = {
        "semanticModels": semantic_models,
        "crossModule": cross_module,
    }
    if discovery_report:
        input_data["discoveryReport"] = discovery_report

    task_instruction = """Analyze the semantic models and produce a prioritized review checklist.

For EVERY function across ALL modules, evaluate:
1. The confidence score of its business rule
2. Whether the Discovery Agent flagged it (implicit rules, gap flags)
3. Its position in the dependency graph (how many modules depend on it)
4. Whether it writes to shared state (session, application scope)
5. Whether it handles authentication or authorization

Rank every item and assign a risk level (CRITICAL/HIGH/MEDIUM/LOW).
Write a specific, actionable review prompt for each — a YES/NO question or a
fill-in-the-blank question that the original developer can answer quickly.

Compute the summary counts and estimate total review time.

Return the complete JSON output matching the output schema."""

    result = runner.run_agent(
        agent_yaml_path=AGENT_YAML,
        input_data=input_data,
        output_path="agents/review-checklist.json",
        task_instruction=task_instruction,
    )

    if result is None:
        return None

    return ReviewChecklist.from_dict(result)
```

---

## 8. Agent 3: Architecture Contradiction Detector

### 8.1 YAML Definition

File: `app/advisory_agents/arch-contradiction-agent.yaml`

```yaml
name: arch-contradiction-agent
advisory: true
appliesTo: ["architecture-decisions"]
stages: [architect]
outputPath: ".modernize/agents/arch-contradictions.json"

systemPrompt: |
  You are an expert in application architecture and service boundary design.
  You receive a proposed target architecture (service group boundaries, API contracts)
  along with the locked semantic model that describes the current application's
  actual behavior.

  Your job is to find CONTRADICTIONS — places where the proposed service boundaries
  will break the application's current behavior. Focus on these 4 contradiction types:

  1. SHARED-TABLE VIOLATION: Two proposed services both write to the same database table.
     This requires deciding table ownership before proceeding.
  2. TIGHT-COUPLING CUT: The proposed boundary cuts through a heavily-used call path
     (5+ calls between the modules being split). This creates excessive cross-service traffic.
  3. SESSION-STATE SPLIT: A module that writes to session/application scope is placed in
     a different service from modules that read those same scope keys.
  4. TRANSACTION BOUNDARY VIOLATION: Modules participating in the same implicit transaction
     (cflock, cftransaction) are placed in different services.

  Severity rules:
  - BLOCKING: shared-table violations where both services WRITE, transaction boundary violations
  - WARNING: shared-table violations where one reads/one writes, tight coupling, session state splits

  For each contradiction, suggest a concrete resolution.

conventions: |
  - ColdFusion transactions: <cftransaction> blocks, <cflock> with scope="application"
  - Session scope: session.* variables — writing in one CFC, reading in another
  - Application scope: application.* variables — shared across all requests
  - Datasource: this.datasource in Application.cfc — determines which DB tables are shared
  - Consider cfinclude as tight coupling (inline dependency)

outputSchema:
  type: object
  required: [contradictions, summary]
  properties:
    contradictions:
      type: array
      items:
        type: object
        required: [type, severity, services, description, evidence, resolution]
        properties:
          type: {type: string, enum: [shared-table, tight-coupling, session-state-split, transaction-boundary]}
          severity: {type: string, enum: [BLOCKING, WARNING]}
          services: {type: array, items: {type: string}}
          description: {type: string}
          evidence:
            type: object
            required: [modules, semanticFact]
            properties:
              modules: {type: array, items: {type: string}}
              semanticFact: {type: string}
          resolution:
            type: object
            required: [option, description]
            properties:
              option: {type: string}
              description: {type: string}
    summary:
      type: object
      required: [blockingCount, warningCount, approvalRecommendation]
      properties:
        blockingCount: {type: integer}
        warningCount: {type: integer}
        approvalRecommendation: {type: string, enum: [approve, revise-and-resubmit]}
```

### 8.2 `advisory/arch_contradiction.py` — Architecture Contradiction Logic

```python
from __future__ import annotations

import json
from pathlib import Path

from core import console
from core.state import ProjectState
from core.models import ArchContradictionReport
from advisory.runner import AdvisoryAgentRunner


AGENT_YAML = str(Path(__file__).parent.parent / "advisory_agents" / "arch-contradiction-agent.yaml")


def run_arch_contradiction(state: ProjectState) -> ArchContradictionReport | None:
    """Run the Architecture Contradiction Detector after Step 5d (design target architecture).

    Reads:
    - .modernize/architecture/architecture-decisions.json (proposed architecture)
    - .modernize/locked/semantic-lock.json (locked semantic model)
    - .modernize/semantics/cross-module.json

    Writes:
    - .modernize/agents/arch-contradictions.json

    Returns:
        ArchContradictionReport or None if agent failed/disabled.
    """
    runner = AdvisoryAgentRunner(state)

    if not runner.is_enabled("arch-contradiction-agent"):
        return None

    # Load required inputs
    arch_decisions = state.read_artifact("architecture", "architecture-decisions.json")
    if not arch_decisions:
        console.print("[yellow]Arch Contradiction Agent: No architecture decisions found. Skipping.[/]")
        return None

    semantic_lock = state.read_artifact("locked", "semantic-lock.json")
    if not semantic_lock:
        console.print("[yellow]Arch Contradiction Agent: Semantics not locked. Skipping.[/]")
        return None

    cross_module = state.read_artifact("semantics", "cross-module.json") or {}

    input_data = {
        "architectureDecisions": arch_decisions,
        "lockedSemantics": semantic_lock,
        "crossModule": cross_module,
    }

    task_instruction = """Compare the proposed architecture (service group boundaries, module assignments)
against the locked semantic model (actual data access patterns, state writes, call graph, transactions).

For each proposed service group boundary, check:
1. Do any two services in the boundary both WRITE to the same table? → shared-table violation
2. Are there modules with 5+ calls between them being split into different services? → tight-coupling cut
3. Does a module that writes to session/application scope end up in a different service
   from modules that read those keys? → session-state split
4. Are modules in the same <cftransaction> or <cflock> block placed in different services?
   → transaction boundary violation

List ALL contradictions found. For each, cite the specific semantic model evidence
(module names, table names, call counts, scope keys).

Suggest a concrete resolution for each (split the table, merge the services, use events, etc).

Set approvalRecommendation to "revise-and-resubmit" if ANY BLOCKING contradictions exist.

Return the complete JSON output matching the output schema."""

    result = runner.run_agent(
        agent_yaml_path=AGENT_YAML,
        input_data=input_data,
        output_path="agents/arch-contradictions.json",
        task_instruction=task_instruction,
    )

    if result is None:
        return None

    return ArchContradictionReport.from_dict(result)
```

---

## 9. Agent 4: Migration Risk Agent

### 9.1 YAML Definition

File: `app/advisory_agents/migration-risk-agent.yaml`

```yaml
name: migration-risk-agent
advisory: true
appliesTo: ["architecture-lock", "semantic-lock"]
stages: [pre-generate]
outputPath: ".modernize/agents/migration-risk-dashboard.json"

systemPrompt: |
  You are an expert in software migration risk assessment. You receive:
  - The locked architecture (service groups, module composition)
  - The locked semantic model (per-module complexity, tables, dependencies, state usage)
  - The Discovery Agent report (gap flags, dead code, implicit rules)

  Your job is to score each service group on 6 risk dimensions (0-100 each),
  compute an overall risk score, recommend a migration sequence, and produce
  an executive summary suitable for a client presentation.

  Risk dimension scoring guide:
  - complexity: Based on aggregate cyclomatic complexity of member modules.
    <10 avg = 0-20, 10-25 avg = 20-50, 25-50 avg = 50-75, >50 avg = 75-100
  - dataSensitivity: Count columns matching PII patterns (email, password, ssn, dob,
    phone, address, credit_card). 0 PII columns = 0, 1-3 = 30, 4-10 = 60, >10 = 85
  - dependencyCount: Inbound + outbound cross-service dependencies.
    0-2 = 0-20, 3-5 = 20-50, 6-10 = 50-75, >10 = 75-100
  - stateEntanglement: Count session/application scope writes needing JWT migration.
    0 = 0, 1-3 = 30, 4-8 = 60, >8 = 85
  - testCoverageGap: Percentage of functions with NO existing test references.
    <10% = 0-20, 10-30% = 20-50, 30-60% = 50-75, >60% = 75-100
  - discoveryGaps: Count of Discovery Agent gap flags in this service group.
    0 = 0, 1-3 = 20, 4-8 = 50, >8 = 75

  Overall risk score = weighted average:
    complexity * 0.15 + dataSensitivity * 0.25 + dependencyCount * 0.15 +
    stateEntanglement * 0.20 + testCoverageGap * 0.15 + discoveryGaps * 0.10

  Risk levels: 0-25 = LOW, 26-50 = MEDIUM, 51-75 = HIGH, 76-100 = CRITICAL

  Migration sequence: recommend starting with lowest-risk leaf services (fewest
  inbound dependencies), ending with highest-risk core services.

conventions: |
  - PII column patterns: email, password, password_hash, ssn, social_security,
    date_of_birth, dob, phone, mobile, address, credit_card, card_number, cvv
  - Complexity is derived from the "complexity" field in semantic models
    (low=5, medium=15, high=30 for estimation)
  - Test references: look for mentions of function names in test fixtures or
    test-like files in the AST

outputSchema:
  type: object
  required: [serviceGroups, recommendedSequence, executiveSummary]
  properties:
    serviceGroups:
      type: array
      items:
        type: object
        required: [name, riskScore, riskLevel, dimensions, topRisks, mitigations]
        properties:
          name: {type: string}
          riskScore: {type: integer, minimum: 0, maximum: 100}
          riskLevel: {type: string, enum: [LOW, MEDIUM, HIGH, CRITICAL]}
          dimensions:
            type: object
            required: [complexity, dataSensitivity, dependencyCount, stateEntanglement, testCoverageGap, discoveryGaps]
            properties:
              complexity: {type: integer, minimum: 0, maximum: 100}
              dataSensitivity: {type: integer, minimum: 0, maximum: 100}
              dependencyCount: {type: integer, minimum: 0, maximum: 100}
              stateEntanglement: {type: integer, minimum: 0, maximum: 100}
              testCoverageGap: {type: integer, minimum: 0, maximum: 100}
              discoveryGaps: {type: integer, minimum: 0, maximum: 100}
          topRisks: {type: array, items: {type: string}}
          mitigations: {type: array, items: {type: string}}
    recommendedSequence: {type: array, items: {type: string}}
    executiveSummary: {type: string}
```

### 9.2 `advisory/migration_risk.py` — Migration Risk Logic

```python
from __future__ import annotations

import json
from pathlib import Path

from core import console
from core.state import ProjectState
from core.models import MigrationRiskDashboard
from core.utils import atomic_write_json
from advisory.runner import AdvisoryAgentRunner


AGENT_YAML = str(Path(__file__).parent.parent / "advisory_agents" / "migration-risk-agent.yaml")


def run_migration_risk(state: ProjectState) -> MigrationRiskDashboard | None:
    """Run the Migration Risk Agent after architecture is locked (pre-generate).

    Reads:
    - .modernize/locked/architecture-lock.json
    - .modernize/locked/semantic-lock.json
    - .modernize/agents/discovery-report.json (optional)

    Writes:
    - .modernize/agents/migration-risk-dashboard.json
    - .modernize/agents/migration-risk-dashboard.md (client deliverable)

    Returns:
        MigrationRiskDashboard or None if agent failed/disabled.
    """
    runner = AdvisoryAgentRunner(state)

    if not runner.is_enabled("migration-risk-agent"):
        return None

    # Load required inputs
    arch_lock = state.read_artifact("locked", "architecture-lock.json")
    if not arch_lock:
        console.print("[yellow]Migration Risk Agent: Architecture not locked. Skipping.[/]")
        return None

    semantic_lock = state.read_artifact("locked", "semantic-lock.json")
    if not semantic_lock:
        console.print("[yellow]Migration Risk Agent: Semantics not locked. Skipping.[/]")
        return None

    # Optional: discovery report
    discovery_report = state.read_artifact("agents", "discovery-report.json")

    input_data = {
        "architectureLock": arch_lock,
        "semanticLock": semantic_lock,
    }
    if discovery_report:
        input_data["discoveryReport"] = discovery_report

    task_instruction = """Score each service group in the architecture on all 6 risk dimensions.

For each service group:
1. List its member modules from the architecture lock
2. Look up each module in the semantic lock to get: complexity, tables, state writes,
   dependencies, function signatures
3. Score each dimension per the scoring guide in your system prompt
4. Compute the weighted overall risk score
5. Identify the top 3 risks (highest scoring dimensions + specific evidence)
6. Suggest concrete mitigations for each top risk

After scoring all service groups:
7. Recommend a migration sequence (lowest risk first, respecting dependency order)
8. Write an executive summary (2-4 sentences) suitable for a client presentation

Return the complete JSON output matching the output schema."""

    result = runner.run_agent(
        agent_yaml_path=AGENT_YAML,
        input_data=input_data,
        output_path="agents/migration-risk-dashboard.json",
        task_instruction=task_instruction,
    )

    if result is None:
        return None

    dashboard = MigrationRiskDashboard.from_dict(result)

    # Generate markdown version (client deliverable)
    md_content = _generate_markdown_report(dashboard)
    md_path = state.modernize_dir / "agents" / "migration-risk-dashboard.md"
    md_path.write_text(md_content, encoding="utf-8")
    console.print(f"[green]Migration Risk dashboard written: agents/migration-risk-dashboard.md[/]")

    return dashboard


def _generate_markdown_report(dashboard: MigrationRiskDashboard) -> str:
    """Generate a markdown version of the migration risk dashboard.

    This is a client deliverable — write it in clear, professional language.
    """
    lines = [
        "# Migration Risk Assessment\n",
        f"## Executive Summary\n\n{dashboard.executive_summary}\n",
        "## Recommended Migration Sequence\n",
    ]

    for i, service in enumerate(dashboard.recommended_sequence, 1):
        lines.append(f"{i}. {service}")
    lines.append("")

    lines.append("## Service Group Risk Scores\n")
    lines.append("| Service Group | Risk Score | Risk Level | Top Risk |")
    lines.append("|---|---|---|---|")

    for sg in dashboard.service_groups:
        top_risk = sg.top_risks[0] if sg.top_risks else "—"
        lines.append(f"| {sg.name} | {sg.risk_score}/100 | {sg.risk_level} | {top_risk} |")

    lines.append("")

    for sg in dashboard.service_groups:
        lines.append(f"### {sg.name} (Risk: {sg.risk_level} — {sg.risk_score}/100)\n")
        lines.append("**Risk Dimensions:**\n")
        lines.append(f"- Complexity: {sg.dimensions.complexity}/100")
        lines.append(f"- Data Sensitivity: {sg.dimensions.data_sensitivity}/100")
        lines.append(f"- Dependency Count: {sg.dimensions.dependency_count}/100")
        lines.append(f"- State Entanglement: {sg.dimensions.state_entanglement}/100")
        lines.append(f"- Test Coverage Gap: {sg.dimensions.test_coverage_gap}/100")
        lines.append(f"- Discovery Gaps: {sg.dimensions.discovery_gaps}/100")
        lines.append("")

        if sg.top_risks:
            lines.append("**Top Risks:**\n")
            for risk in sg.top_risks:
                lines.append(f"- {risk}")
            lines.append("")

        if sg.mitigations:
            lines.append("**Recommended Mitigations:**\n")
            for mitigation in sg.mitigations:
                lines.append(f"- {mitigation}")
            lines.append("")

    return "\n".join(lines)
```

---

## 10. Agent 5: Security Audit Agent

### 10.1 YAML Definition

File: `app/advisory_agents/security-audit-agent.yaml`

```yaml
name: security-audit-agent
advisory: true
appliesTo: ["generated-code"]
stages: [post-generate]
outputPath: ".modernize/agents/{service}/security-audit.json"

systemPrompt: |
  You are a security auditor specializing in legacy-to-modern application migration.
  You receive generated code (Go backend + React frontend) alongside the locked
  semantic model that describes the original application's security properties.

  Your job is to verify that the generated code PRESERVES the security properties
  declared in the locked semantic model. You check for 5 categories of security drift:

  1. AUTH-DRIFT: The locked model records session scope writes (session.userId,
     session.userRole, etc). The generated code uses JWT. Verify ALL session scope
     writes are mapped to JWT claims. Flag any that are missing.

  2. SQL-INJECTION: The locked model marks queries as parameterized=true. Verify the
     generated Go code uses parameterized queries (sqlc, database/sql with $1 placeholders).
     Flag any string concatenation in SQL.

  3. DATA-EXPOSURE: The locked model specifies function outputs (return types). Verify
     the generated API response structs don't expose fields beyond what the locked
     outputs specify. Especially flag: password_hash, internal IDs, session tokens.

  4. XSS: Verify React components use JSX (auto-escaped) and don't use
     dangerouslySetInnerHTML. Verify Go templates use html/template (auto-escaped).

  5. MISSING-AUTH: The locked model marks function access as "public" or "private".
     Verify that "private" functions have auth middleware applied in the generated
     router/handler code.

  Severity guide:
  - CRITICAL: SQL injection found, auth completely missing on private endpoint
  - HIGH: Auth drift (missing JWT claims), data exposure (PII leaked)
  - MEDIUM: Partial auth drift, unnecessary fields in responses
  - LOW: Style issues, non-security-relevant findings

conventions: |
  - Go backend: Chi router, sqlc for queries, JWT middleware
  - React frontend: JSX auto-escaping, no dangerouslySetInnerHTML
  - Auth middleware pattern: r.Group(func(r chi.Router) { r.Use(authMiddleware) ... })
  - Parameterized queries: sqlc generated code uses $1, $2 placeholders
  - Response DTOs should match locked outputs — no extra fields

outputSchema:
  type: object
  required: [findings, summary]
  properties:
    findings:
      type: array
      items:
        type: object
        required: [severity, category, file, lineRange, description, semanticEvidence, remediation]
        properties:
          severity: {type: string, enum: [CRITICAL, HIGH, MEDIUM, LOW]}
          category: {type: string, enum: [auth-drift, sql-injection, data-exposure, xss, missing-auth]}
          file: {type: string}
          lineRange: {type: string}
          description: {type: string}
          semanticEvidence: {type: string}
          remediation: {type: string}
    summary:
      type: object
      required: [criticalCount, highCount, mediumCount, lowCount, passRate, approvalRecommendation]
      properties:
        criticalCount: {type: integer}
        highCount: {type: integer}
        mediumCount: {type: integer}
        lowCount: {type: integer}
        passRate: {type: integer, minimum: 0, maximum: 100}
        approvalRecommendation: {type: string, enum: [approve, approve-with-fixes, revise-and-resubmit]}
```

### 10.2 `advisory/security_audit.py` — Security Audit Logic

```python
from __future__ import annotations

import json
from pathlib import Path

from core import console
from core.state import ProjectState
from core.models import SecurityAuditReport
from core.utils import atomic_write_json
from advisory.runner import AdvisoryAgentRunner


AGENT_YAML = str(Path(__file__).parent.parent / "advisory_agents" / "security-audit-agent.yaml")


def run_security_audit(state: ProjectState, service_name: str) -> SecurityAuditReport | None:
    """Run the Security Audit Agent after code generation for a service group.

    Reads:
    - .modernize/services/<service>/ (all generated code files)
    - .modernize/locked/semantic-lock.json (security properties)
    - Target adapter conventions

    Writes:
    - .modernize/agents/<service>/security-audit.json
    - .modernize/agents/<service>/security-audit.md

    Args:
        service_name: The service group to audit (e.g., "users-service").

    Returns:
        SecurityAuditReport or None if agent failed/disabled.
    """
    runner = AdvisoryAgentRunner(state)

    if not runner.is_enabled("security-audit-agent"):
        return None

    # Load generated code
    service_dir = state.modernize_dir / "services" / service_name
    if not service_dir.exists():
        console.print(f"[yellow]Security Audit: No generated code for {service_name}. Skipping.[/]")
        return None

    generated_files = {}
    for code_file in service_dir.rglob("*"):
        if code_file.is_file() and code_file.suffix in (".go", ".tsx", ".ts", ".jsx", ".js"):
            relative_path = str(code_file.relative_to(state.modernize_dir))
            try:
                generated_files[relative_path] = code_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

    if not generated_files:
        console.print(f"[yellow]Security Audit: No code files found in {service_name}. Skipping.[/]")
        return None

    # Load locked semantics
    semantic_lock = state.read_artifact("locked", "semantic-lock.json")
    if not semantic_lock:
        console.print("[yellow]Security Audit: Semantics not locked. Skipping.[/]")
        return None

    # Filter semantic lock to modules in this service group
    arch = state.read_artifact("architecture", "architecture-decisions.json") or {}
    service_modules = _get_modules_for_service(arch, service_name)

    relevant_semantics = {}
    for module_name, locked_module in semantic_lock.get("modules", {}).items():
        if module_name in service_modules:
            relevant_semantics[module_name] = locked_module

    input_data = {
        "generatedCode": generated_files,
        "lockedSemantics": relevant_semantics,
        "serviceName": service_name,
    }

    task_instruction = f"""Audit the generated code for service "{service_name}" against the locked semantic model.

For each module in the locked semantics:
1. Find the corresponding generated code files
2. Check AUTH-DRIFT: Compare locked stateWrites (session.*) against JWT claims in generated auth code
3. Check SQL-INJECTION: Verify all queries marked parameterized=true use parameterized bindings
4. Check DATA-EXPOSURE: Compare locked function outputs against generated response structs
5. Check XSS: Verify React components don't use dangerouslySetInnerHTML
6. Check MISSING-AUTH: Verify private functions have auth middleware in the router

For each finding, cite:
- The specific file and approximate line range in the generated code
- The specific semantic model evidence (locked field values)
- A concrete remediation action

Compute passRate as: (total checks performed - findings count) / total checks * 100

Set approvalRecommendation:
- "approve" if no CRITICAL or HIGH findings
- "approve-with-fixes" if HIGH but no CRITICAL findings
- "revise-and-resubmit" if any CRITICAL findings

Return the complete JSON output matching the output schema."""

    output_path = f"agents/{service_name}/security-audit.json"
    result = runner.run_agent(
        agent_yaml_path=AGENT_YAML,
        input_data=input_data,
        output_path=output_path,
        task_instruction=task_instruction,
    )

    if result is None:
        return None

    report = SecurityAuditReport.from_dict(result)

    # Generate markdown version
    md_content = _generate_security_markdown(report, service_name)
    md_path = state.modernize_dir / "agents" / service_name / "security-audit.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_content, encoding="utf-8")

    return report


def _get_modules_for_service(arch: dict, service_name: str) -> set[str]:
    """Extract module names belonging to a service group from architecture decisions."""
    for sg in arch.get("serviceGroups", []):
        if sg.get("name") == service_name:
            return set(sg.get("modules", []))
    return set()


def _generate_security_markdown(report: SecurityAuditReport, service_name: str) -> str:
    """Generate a markdown security audit report."""
    lines = [
        f"# Security Audit: {service_name}\n",
        f"**Pass Rate:** {report.pass_rate}%  ",
        f"**Recommendation:** {report.approval_recommendation}\n",
        f"| Severity | Count |",
        f"|---|---|",
        f"| CRITICAL | {report.critical_count} |",
        f"| HIGH | {report.high_count} |",
        f"| MEDIUM | {report.medium_count} |",
        f"| LOW | {report.low_count} |",
        "",
    ]

    if report.findings:
        lines.append("## Findings\n")
        for i, finding in enumerate(report.findings, 1):
            lines.append(f"### {i}. [{finding.severity}] {finding.category}\n")
            lines.append(f"**File:** `{finding.file}` (lines {finding.line_range})  ")
            lines.append(f"**Description:** {finding.description}  ")
            lines.append(f"**Evidence:** {finding.semantic_evidence}  ")
            lines.append(f"**Remediation:** {finding.remediation}\n")
    else:
        lines.append("## No findings — all checks passed.\n")

    return "\n".join(lines)
```

---

## 11. Agent 6: Test Generation Agent

### 11.1 YAML Definition

File: `app/advisory_agents/test-generation-agent.yaml`

```yaml
name: test-generation-agent
advisory: true
appliesTo: ["generated-code", "semantic-lock"]
stages: [verify]
outputPath: ".modernize/agents/{service}/test-manifest.json"

systemPrompt: |
  You are an expert test engineer specializing in generating tests for migrated applications.
  You receive locked semantic models (approved business rules, function signatures, control flow)
  and the generated code. Your job is to produce two categories of tests:

  1. BEHAVIORAL EQUIVALENCE TESTS: For each locked function signature (inputs → outputs),
     generate a test that asserts the new code produces the expected output shape.
     These tests verify the migration preserved the function contract.

  2. BUSINESS RULE UNIT TESTS: For each locked business rule AND control flow rule,
     generate one test per rule. Name each test after the business rule.
     Control flow facts (conditions → actions) become test cases.

  Test generation rules:
  - Go tests: Use standard library testing package. No external test frameworks.
    Follow Go conventions: TestFunctionName_Scenario pattern.
  - TypeScript tests: Use vitest. Follow React Testing Library conventions.
  - Every test must have a comment citing its source:
    "// From locked mapping: <function signature>" or
    "// From locked business rule: <rule name>"
  - Use table-driven tests in Go when a function has multiple input/output scenarios.
  - Mock external dependencies (database, HTTP clients) with interfaces.
  - Do NOT generate tests for dead code flagged by Discovery Agent.

conventions: |
  - Go test file naming: <module>_test.go
  - TypeScript test file naming: <Component>.spec.ts or <Component>.spec.tsx
  - Go mock pattern: define interface, create mock struct implementing it
  - React test pattern: render component, assert on screen queries
  - Business rule test naming: TestUserAuthentication_ValidCredentials (PascalCase)
  - Use t.Run() for subtests in Go
  - Use describe/it blocks in TypeScript

outputSchema:
  type: object
  required: [testFiles, coverage]
  properties:
    testFiles:
      type: array
      items:
        type: object
        required: [path, language, testCount, categories]
        properties:
          path: {type: string}
          language: {type: string, enum: [go, typescript]}
          testCount: {type: integer}
          categories:
            type: object
            required: [equivalenceTests, businessRuleTests]
            properties:
              equivalenceTests: {type: integer}
              businessRuleTests: {type: integer}
    coverage:
      type: object
      required: [businessRulesWithTests, totalBusinessRules, coveragePercent]
      properties:
        businessRulesWithTests: {type: integer}
        totalBusinessRules: {type: integer}
        coveragePercent: {type: number, minimum: 0, maximum: 100}
```

### 11.2 `advisory/test_generation.py` — Test Generation Logic

```python
from __future__ import annotations

import json
from pathlib import Path

from core import console
from core.state import ProjectState
from core.models import TestManifest
from core.utils import atomic_write_json
from advisory.runner import AdvisoryAgentRunner


AGENT_YAML = str(Path(__file__).parent.parent / "advisory_agents" / "test-generation-agent.yaml")


def run_test_generation(state: ProjectState, service_name: str) -> TestManifest | None:
    """Run the Test Generation Agent alongside the Verifier Module.

    Reads:
    - .modernize/locked/semantic-lock.json (function signatures, business rules, control flow)
    - .modernize/services/<service>/ (generated code — to reference actual function names/types)
    - .modernize/agents/discovery-report.json (optional — to skip dead code)
    - .modernize/recordings/<service>/ (optional — behavioral recording data)

    Writes:
    - .modernize/agents/<service>/test-suite-supplement_test.go (Go tests)
    - .modernize/agents/<service>/test-suite-supplement.spec.ts (TypeScript tests)
    - .modernize/agents/<service>/test-manifest.json (coverage summary)

    Args:
        service_name: The service group to generate tests for.

    Returns:
        TestManifest or None if agent failed/disabled.
    """
    runner = AdvisoryAgentRunner(state)

    if not runner.is_enabled("test-generation-agent"):
        return None

    # Load locked semantics
    semantic_lock = state.read_artifact("locked", "semantic-lock.json")
    if not semantic_lock:
        console.print("[yellow]Test Generation: Semantics not locked. Skipping.[/]")
        return None

    # Filter to modules in this service
    arch = state.read_artifact("architecture", "architecture-decisions.json") or {}
    service_modules = _get_modules_for_service(arch, service_name)

    relevant_semantics = {}
    for module_name, locked_module in semantic_lock.get("modules", {}).items():
        if module_name in service_modules:
            relevant_semantics[module_name] = locked_module

    if not relevant_semantics:
        console.print(f"[yellow]Test Generation: No locked modules for {service_name}. Skipping.[/]")
        return None

    # Load generated code for reference
    service_dir = state.modernize_dir / "services" / service_name
    generated_files = {}
    if service_dir.exists():
        for code_file in service_dir.rglob("*"):
            if code_file.is_file() and code_file.suffix in (".go", ".tsx", ".ts"):
                relative_path = str(code_file.relative_to(state.modernize_dir))
                try:
                    generated_files[relative_path] = code_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue

    # Optional: discovery report (to skip dead code)
    discovery_report = state.read_artifact("agents", "discovery-report.json")
    dead_functions = set()
    if discovery_report:
        for entry in discovery_report.get("deadCode", []):
            dead_functions.add(f"{entry['module']}.{entry['function']}")

    # Determine target stack
    migration = state.load()
    target_stack = migration.get("targetStack", {})

    input_data = {
        "lockedSemantics": relevant_semantics,
        "generatedCode": generated_files,
        "serviceName": service_name,
        "targetStack": target_stack,
        "deadFunctions": list(dead_functions),
    }

    task_instruction = f"""Generate tests for service "{service_name}".

For each module in the locked semantics (SKIP functions listed in deadFunctions):

1. EQUIVALENCE TESTS: For each function with a locked signature (inputs → outputs),
   generate a test that:
   - Creates mock inputs matching the locked input types
   - Calls the generated function
   - Asserts the output matches the locked output shape
   - Comment: "// From locked mapping: <function signature>"

2. BUSINESS RULE TESTS: For each function with locked businessRule and controlFlow:
   - Generate one test per business rule
   - Generate one test per control flow rule (condition → action)
   - Name tests after the business rule: TestUserAuthentication_ValidCredentials
   - Comment: "// From locked business rule: <rule name>"

Generate Go test code if the target backend is "go".
Generate TypeScript test code if the target frontend is "react".

Return:
1. The test manifest JSON (matching the output schema) with file paths, counts, and coverage
2. Include the actual test code as string content in a "testCode" field for each testFile entry
   (this is outside the schema — the runner will extract and write the files separately)

Return the complete JSON output matching the output schema."""

    result = runner.run_agent(
        agent_yaml_path=AGENT_YAML,
        input_data=input_data,
        output_path=f"agents/{service_name}/test-manifest.json",
        task_instruction=task_instruction,
    )

    if result is None:
        return None

    # Extract and write test code files if present in the response
    _write_test_files(state, service_name, result, target_stack)

    manifest = TestManifest.from_dict(result)
    return manifest


def _get_modules_for_service(arch: dict, service_name: str) -> set[str]:
    """Extract module names belonging to a service group."""
    for sg in arch.get("serviceGroups", []):
        if sg.get("name") == service_name:
            return set(sg.get("modules", []))
    return set()


def _write_test_files(state: ProjectState, service_name: str,
                      result: dict, target_stack: dict) -> None:
    """Extract test code from agent response and write to files.

    The agent may include a 'testCode' field alongside each testFile entry.
    If so, write the code to the appropriate file path.
    """
    agents_service_dir = state.modernize_dir / "agents" / service_name
    agents_service_dir.mkdir(parents=True, exist_ok=True)

    for test_file in result.get("testFiles", []):
        code = test_file.get("testCode") or result.get("testCode", {}).get(test_file.get("path", ""))
        if code:
            file_path = agents_service_dir / Path(test_file["path"]).name
            file_path.write_text(code, encoding="utf-8")
            console.print(f"  Written: {file_path.relative_to(state.modernize_dir)}")

    # Also write standard filenames as fallback
    backend = target_stack.get("backend", "go")
    frontend = target_stack.get("frontend", "react")

    go_code = result.get("goTestCode")
    if go_code:
        go_path = agents_service_dir / "test-suite-supplement_test.go"
        go_path.write_text(go_code, encoding="utf-8")

    ts_code = result.get("typescriptTestCode")
    if ts_code:
        ts_path = agents_service_dir / "test-suite-supplement.spec.ts"
        ts_path.write_text(ts_code, encoding="utf-8")
```

---

## 12. Pipeline Integration Points

These are the exact hooks into existing v2 pipeline modules. Each hook runs the advisory agent **after** its host stage completes, in a non-blocking manner.

### 12.1 `pipeline/extractor.py` — Hook for Discovery Agent

Add at the end of `run_extract()`, after all extractions and the consistency check:

```python
# At the end of run_extract(), add:
from advisory.discovery import run_discovery

# Run Discovery Agent (non-blocking — pipeline continues regardless)
try:
    discovery_report = run_discovery(state)
    if discovery_report:
        console.print(f"[blue]Discovery Agent found: {len(discovery_report.business_rules)} business rules, "
                      f"{len(discovery_report.cross_module_patterns)} patterns, "
                      f"{len(discovery_report.gap_flags)} gaps[/]")
except Exception as e:
    console.print(f"[yellow]Discovery Agent failed (non-blocking): {e}[/]")
```

### 12.2 `pipeline/documenter.py` — Hook for Review Prioritizer

Add at the end of `run_document()`:

```python
# At the end of run_document(), add:
from advisory.review_prioritizer import run_review_prioritizer

try:
    checklist = run_review_prioritizer(state)
    if checklist and checklist.summary:
        console.print(f"[blue]Review Prioritizer: {checklist.summary.critical_count} CRITICAL, "
                      f"{checklist.summary.high_count} HIGH items. "
                      f"Est. review time: {checklist.summary.estimated_review_minutes} min[/]")
except Exception as e:
    console.print(f"[yellow]Review Prioritizer failed (non-blocking): {e}[/]")
```

### 12.3 `pipeline/architect.py` — Hook for Arch Contradiction Detector

Add at the end of `run_architect_target()` (Step 5d), BEFORE the step is marked as completed:

```python
# At the end of run_architect_target(), after writing architecture-decisions.json:
from advisory.arch_contradiction import run_arch_contradiction

try:
    contradictions = run_arch_contradiction(state)
    if contradictions:
        if contradictions.blocking_count > 0:
            console.print(f"[red]WARNING: {contradictions.blocking_count} BLOCKING architecture contradictions found![/]")
            console.print(f"[red]Review with: modernize agents arch-contradictions[/]")
        elif contradictions.warning_count > 0:
            console.print(f"[yellow]{contradictions.warning_count} architecture warnings found. "
                          f"Review with: modernize agents arch-contradictions[/]")
except Exception as e:
    console.print(f"[yellow]Arch Contradiction Agent failed (non-blocking): {e}[/]")
```

### 12.4 `pipeline/generator.py` — Hook for Migration Risk (pre-generate) and Security Audit (post-generate)

**Pre-generate hook** — add at the START of `run_generate()`:

```python
# At the start of run_generate(), after acquiring the file lock:
from advisory.migration_risk import run_migration_risk

# Run Migration Risk Agent (only once, not per-service — check if already run)
risk_dashboard_path = state.modernize_dir / "agents" / "migration-risk-dashboard.json"
if not risk_dashboard_path.exists():
    try:
        risk_dashboard = run_migration_risk(state)
        if risk_dashboard:
            # Find this service's risk
            for sg in risk_dashboard.service_groups:
                if sg.name == service_name:
                    console.print(f"[blue]Migration Risk: {sg.risk_level} ({sg.risk_score}/100) — "
                                  f"{len(sg.top_risks)} top risks identified[/]")
                    break
    except Exception as e:
        console.print(f"[yellow]Migration Risk Agent failed (non-blocking): {e}[/]")
```

**Post-generate hook** — add at the END of `run_generate()`, before releasing the file lock:

```python
# At the end of run_generate(), before releasing the lock:
from advisory.security_audit import run_security_audit

try:
    security_report = run_security_audit(state, service_name)
    if security_report:
        if security_report.critical_count > 0:
            console.print(f"[red]Security Audit: {security_report.critical_count} CRITICAL findings![/]")
        console.print(f"[blue]Security Audit: Pass rate {security_report.pass_rate}%, "
                      f"recommendation: {security_report.approval_recommendation}[/]")
except Exception as e:
    console.print(f"[yellow]Security Audit Agent failed (non-blocking): {e}[/]")
```

### 12.5 `pipeline/verifier.py` — Hook for Test Generation

Add at the start of `run_verify()`:

```python
# At the start of run_verify(), run test generation in parallel:
from advisory.test_generation import run_test_generation

try:
    test_manifest = run_test_generation(state, service_name)
    if test_manifest and test_manifest.coverage:
        console.print(f"[blue]Test Generation: {test_manifest.coverage.business_rules_with_tests}/"
                      f"{test_manifest.coverage.total_business_rules} business rules covered "
                      f"({test_manifest.coverage.coverage_percent:.0f}%)[/]")
except Exception as e:
    console.print(f"[yellow]Test Generation Agent failed (non-blocking): {e}[/]")
```

### 12.6 `pipeline/reviewer.py` — Show Prioritized Checklist

Update `run_review_semantics()` to show the prioritized checklist if it exists:

```python
# In run_review_semantics(), if --prioritized flag is set:
def run_review_semantics(state: ProjectState, module: str | None = None,
                         prioritized: bool = False) -> None:
    """Step 4 — Review semantics with original developers.

    If --prioritized: show only CRITICAL and HIGH items from the review checklist.
    """
    if prioritized:
        checklist = state.read_artifact("agents", "review-checklist.json")
        if checklist:
            items = checklist.get("checklist", [])
            high_priority = [i for i in items if i["riskLevel"] in ("CRITICAL", "HIGH")]
            table = Table(title="Prioritized Review Items")
            table.add_column("Rank", style="bold")
            table.add_column("Risk", style="red")
            table.add_column("Module")
            table.add_column("Function")
            table.add_column("Review Prompt")
            for item in high_priority:
                table.add_row(
                    str(item["rank"]),
                    item["riskLevel"],
                    item["module"],
                    item["function"],
                    item["reviewPrompt"],
                )
            console.print(table)
            return
        else:
            console.print("[yellow]No review checklist available. Run extraction first.[/]")

    # ... existing review logic ...
```

### 12.7 `pipeline/architect.py` — Show Contradictions in Architecture Review

Update the architecture review display to show contradictions:

```python
# In run_review_architect() or wherever architecture review is displayed:
def _show_architecture_review(state: ProjectState) -> None:
    """Display architecture for review, including contradiction warnings."""
    # ... existing architecture display ...

    # Show contradiction summary if available
    contradictions = state.read_artifact("agents", "arch-contradictions.json")
    if contradictions:
        summary = contradictions.get("summary", {})
        blocking = summary.get("blockingCount", 0)
        warnings = summary.get("warningCount", 0)

        if blocking > 0:
            console.print(f"\n[red bold]BLOCKING CONTRADICTIONS: {blocking}[/]")
            console.print("[red]These must be resolved before approving the architecture.[/]")
            for c in contradictions.get("contradictions", []):
                if c["severity"] == "BLOCKING":
                    console.print(f"  [{c['type']}] {c['description']}")
                    console.print(f"    Resolution: {c['resolution']['description']}")

        if warnings > 0:
            console.print(f"\n[yellow]Warnings: {warnings}[/]")
            for c in contradictions.get("contradictions", []):
                if c["severity"] == "WARNING":
                    console.print(f"  [{c['type']}] {c['description']}")

        console.print(f"\nFull report: modernize agents arch-contradictions")
```

---

## 13. CLI Additions

Add these commands to `modernize.py`. All advisory agent commands are grouped under the `agents` subcommand.

### 13.1 `agents` Subgroup

```python
@cli.group()
@click.pass_context
def agents(ctx):
    """Advisory agent commands — view reports, run agents, manage configuration."""
    pass
```

### 13.2 Agent Report Commands

```python
@agents.command("discovery-report")
@click.pass_context
def agents_discovery_report(ctx):
    """Display the Discovery Agent report."""
    state = ProjectState(ctx.obj["project_dir"])
    report = state.read_artifact("agents", "discovery-report.json")
    if not report:
        console.print("[yellow]No discovery report found. Run 'modernize extract' first.[/]")
        return

    dr = DiscoveryReport.from_dict(report)
    console.print(f"\n[bold]Discovery Report[/]")
    console.print(f"  Business rules found: {len(dr.business_rules)}")
    console.print(f"  Cross-module patterns: {len(dr.cross_module_patterns)}")
    console.print(f"  Implicit rules: {len(dr.implicit_rules)}")
    console.print(f"  Dead code entries: {len(dr.dead_code)}")
    console.print(f"  Gap flags: {len(dr.gap_flags)}")

    if dr.cross_module_patterns:
        console.print("\n[bold]Cross-Module Patterns:[/]")
        for p in dr.cross_module_patterns:
            console.print(f"  {p.pattern_name}: {p.description}")
            console.print(f"    Modules: {', '.join(p.modules)}")
            console.print(f"    Recommendation: {p.recommendation}")

    if dr.gap_flags:
        console.print("\n[bold]Gap Flags (need human input):[/]")
        for g in dr.gap_flags:
            console.print(f"  {g.module}.{g.function} — {g.field}: {g.suggestion}")


@agents.command("review-checklist")
@click.pass_context
def agents_review_checklist(ctx):
    """Display the full prioritized review checklist."""
    state = ProjectState(ctx.obj["project_dir"])
    report = state.read_artifact("agents", "review-checklist.json")
    if not report:
        console.print("[yellow]No review checklist found. Run 'modernize document' first.[/]")
        return

    checklist = ReviewChecklist.from_dict(report)
    table = Table(title="Review Checklist")
    table.add_column("#", style="bold")
    table.add_column("Risk")
    table.add_column("Module")
    table.add_column("Function")
    table.add_column("Review Prompt")
    table.add_column("Reason")

    for item in checklist.checklist:
        risk_style = {"CRITICAL": "red bold", "HIGH": "red", "MEDIUM": "yellow", "LOW": "dim"}.get(item.risk_level, "")
        table.add_row(
            str(item.rank),
            f"[{risk_style}]{item.risk_level}[/]",
            item.module,
            item.function,
            item.review_prompt[:80] + "..." if len(item.review_prompt) > 80 else item.review_prompt,
            item.risk_reason[:60] + "..." if len(item.risk_reason) > 60 else item.risk_reason,
        )

    console.print(table)

    if checklist.summary:
        s = checklist.summary
        console.print(f"\nTotal: {s.total_items} items — "
                      f"{s.critical_count} CRITICAL, {s.high_count} HIGH, "
                      f"{s.medium_count} MEDIUM, {s.low_count} LOW")
        console.print(f"Estimated review time: {s.estimated_review_minutes} minutes")


@agents.command("arch-contradictions")
@click.pass_context
def agents_arch_contradictions(ctx):
    """Display architecture contradiction report."""
    state = ProjectState(ctx.obj["project_dir"])
    report = state.read_artifact("agents", "arch-contradictions.json")
    if not report:
        console.print("[yellow]No contradiction report found. Run 'modernize architect --target' first.[/]")
        return

    cr = ArchContradictionReport.from_dict(report)
    console.print(f"\n[bold]Architecture Contradictions[/]")
    console.print(f"  Blocking: {cr.blocking_count}")
    console.print(f"  Warnings: {cr.warning_count}")
    console.print(f"  Recommendation: {cr.approval_recommendation}")

    for c in cr.contradictions:
        severity_style = "red bold" if c.severity == "BLOCKING" else "yellow"
        console.print(f"\n  [{severity_style}][{c.severity}] {c.contradiction_type}[/]")
        console.print(f"  Services: {', '.join(c.services)}")
        console.print(f"  {c.description}")
        console.print(f"  Evidence: {c.evidence.semantic_fact}")
        console.print(f"  Resolution ({c.resolution.option}): {c.resolution.description}")


@agents.command("risk-dashboard")
@click.pass_context
def agents_risk_dashboard(ctx):
    """Display the migration risk dashboard."""
    state = ProjectState(ctx.obj["project_dir"])
    report = state.read_artifact("agents", "migration-risk-dashboard.json")
    if not report:
        console.print("[yellow]No risk dashboard found. Run 'modernize agents risk-dashboard --generate' "
                      "or wait until architecture is locked.[/]")
        return

    dashboard = MigrationRiskDashboard.from_dict(report)
    console.print(f"\n[bold]Migration Risk Dashboard[/]")
    console.print(f"\n{dashboard.executive_summary}\n")

    table = Table(title="Service Group Risk Scores")
    table.add_column("Service Group")
    table.add_column("Score")
    table.add_column("Level")
    table.add_column("Top Risk")

    for sg in dashboard.service_groups:
        level_style = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "red bold"}.get(sg.risk_level, "")
        top_risk = sg.top_risks[0] if sg.top_risks else "—"
        table.add_row(sg.name, f"{sg.risk_score}/100", f"[{level_style}]{sg.risk_level}[/]", top_risk)

    console.print(table)

    console.print(f"\n[bold]Recommended migration sequence:[/]")
    for i, service in enumerate(dashboard.recommended_sequence, 1):
        console.print(f"  {i}. {service}")

    console.print(f"\nFull report: .modernize/agents/migration-risk-dashboard.md")


@agents.command("security-audit")
@click.argument("service")
@click.pass_context
def agents_security_audit(ctx, service):
    """Display security audit report for a service group."""
    state = ProjectState(ctx.obj["project_dir"])
    report = state.read_artifact(f"agents/{service}", "security-audit.json")
    if not report:
        console.print(f"[yellow]No security audit found for {service}. Run 'modernize generate {service}' first.[/]")
        return

    sr = SecurityAuditReport.from_dict(report)
    console.print(f"\n[bold]Security Audit: {service}[/]")
    console.print(f"  Pass rate: {sr.pass_rate}%")
    console.print(f"  Recommendation: {sr.approval_recommendation}")

    if sr.findings:
        table = Table(title="Security Findings")
        table.add_column("Severity")
        table.add_column("Category")
        table.add_column("File")
        table.add_column("Description")
        table.add_column("Remediation")

        for f in sr.findings:
            sev_style = {"CRITICAL": "red bold", "HIGH": "red", "MEDIUM": "yellow", "LOW": "dim"}.get(f.severity, "")
            table.add_row(
                f"[{sev_style}]{f.severity}[/]",
                f.category,
                f"{f.file}:{f.line_range}",
                f.description[:60] + "...",
                f.remediation[:60] + "...",
            )
        console.print(table)

    console.print(f"\nFull report: .modernize/agents/{service}/security-audit.md")


@agents.command("generate-tests")
@click.argument("service")
@click.pass_context
def agents_generate_tests(ctx, service):
    """Generate supplemental tests for a service group."""
    state = ProjectState(ctx.obj["project_dir"])
    from advisory.test_generation import run_test_generation
    manifest = run_test_generation(state, service)
    if manifest and manifest.coverage:
        console.print(f"[green]Tests generated for {service}[/]")
        console.print(f"  Coverage: {manifest.coverage.business_rules_with_tests}/"
                      f"{manifest.coverage.total_business_rules} business rules "
                      f"({manifest.coverage.coverage_percent:.0f}%)")
        for tf in manifest.test_files:
            console.print(f"  {tf.path}: {tf.test_count} tests ({tf.equivalence_tests} equivalence, "
                          f"{tf.business_rule_tests} business rule)")
    else:
        console.print(f"[yellow]No tests generated for {service}.[/]")


@agents.command("test-coverage")
@click.argument("service")
@click.pass_context
def agents_test_coverage(ctx, service):
    """Display test coverage against business rules for a service group."""
    state = ProjectState(ctx.obj["project_dir"])
    report = state.read_artifact(f"agents/{service}", "test-manifest.json")
    if not report:
        console.print(f"[yellow]No test manifest found for {service}. "
                      f"Run 'modernize agents generate-tests {service}' first.[/]")
        return

    manifest = TestManifest.from_dict(report)
    if manifest.coverage:
        c = manifest.coverage
        console.print(f"\n[bold]Test Coverage: {service}[/]")
        console.print(f"  Business rules with tests: {c.business_rules_with_tests}/{c.total_business_rules}")
        console.print(f"  Coverage: {c.coverage_percent:.0f}%")
    for tf in manifest.test_files:
        console.print(f"  {tf.path}: {tf.test_count} tests")
```

### 13.3 Agent Configuration Commands

```python
@agents.command("list")
@click.pass_context
def agents_list(ctx):
    """List all advisory agents and their status (enabled/disabled)."""
    state = ProjectState(ctx.obj["project_dir"])
    migration = state.load()
    config = AdvisoryAgentConfig.from_dict(migration)

    table = Table(title="Advisory Agents")
    table.add_column("Agent")
    table.add_column("Status")
    table.add_column("Stage")
    table.add_column("Output")

    agent_info = [
        ("discovery-agent", "extract", "agents/discovery-report.json"),
        ("review-prioritizer-agent", "document", "agents/review-checklist.json"),
        ("arch-contradiction-agent", "architect", "agents/arch-contradictions.json"),
        ("migration-risk-agent", "pre-generate", "agents/migration-risk-dashboard.json"),
        ("security-audit-agent", "post-generate", "agents/<service>/security-audit.json"),
        ("test-generation-agent", "verify", "agents/<service>/test-manifest.json"),
    ]

    for name, stage, output in agent_info:
        enabled = config.is_enabled(name)
        status = "[green]enabled[/]" if enabled else "[red]disabled[/]"
        # Check if output exists
        has_output = ""
        if "<service>" not in output:
            if (state.modernize_dir / output).exists():
                has_output = " (has output)"
        table.add_row(name, status + has_output, stage, output)

    console.print(table)


@agents.command("disable")
@click.argument("agent_name")
@click.pass_context
def agents_disable(ctx, agent_name):
    """Disable an advisory agent."""
    state = ProjectState(ctx.obj["project_dir"])
    migration = state.load()
    config = AdvisoryAgentConfig.from_dict(migration)

    if agent_name not in config.enabled:
        console.print(f"[red]Unknown agent: {agent_name}[/]")
        console.print(f"Available: {', '.join(config.enabled.keys())}")
        return

    config.disable(agent_name)
    migration.update(config.to_dict())
    state.save(migration)
    console.print(f"[yellow]Disabled: {agent_name}[/]")


@agents.command("enable")
@click.argument("agent_name")
@click.pass_context
def agents_enable(ctx, agent_name):
    """Enable an advisory agent."""
    state = ProjectState(ctx.obj["project_dir"])
    migration = state.load()
    config = AdvisoryAgentConfig.from_dict(migration)

    if agent_name not in config.enabled:
        console.print(f"[red]Unknown agent: {agent_name}[/]")
        console.print(f"Available: {', '.join(config.enabled.keys())}")
        return

    config.enable(agent_name)
    migration.update(config.to_dict())
    state.save(migration)
    console.print(f"[green]Enabled: {agent_name}[/]")
```

### 13.4 Updated `review semantics` Command

```python
# Update the existing review semantics command to add --prioritized flag:
@cli.command("review")
@click.argument("target", type=click.Choice(["semantics", "architect", "generate"]))
@click.argument("module_or_service", required=False)
@click.option("--prioritized", is_flag=True, help="Show only CRITICAL and HIGH priority items")
@click.pass_context
def review(ctx, target, module_or_service, prioritized):
    """Review pipeline stage output."""
    state = ProjectState(ctx.obj["project_dir"])
    if target == "semantics":
        run_review_semantics(state, module=module_or_service, prioritized=prioritized)
    elif target == "architect":
        _show_architecture_review(state)
    elif target == "generate":
        # Show security audit summary before code review
        if module_or_service:
            security = state.read_artifact(f"agents/{module_or_service}", "security-audit.json")
            if security:
                sr = SecurityAuditReport.from_dict(security)
                console.print(f"[blue]Security Audit: {sr.critical_count} CRITICAL, {sr.high_count} HIGH. "
                              f"Review: .modernize/agents/{module_or_service}/security-audit.md[/]")
        # ... existing code review logic ...
```

---

## 14. Testing Strategy

### 14.1 Unit Tests for Advisory Runner

File: `app/tests/unit/test_advisory_runner.py`

```python
def test_advisory_runner_skips_disabled_agent(tmp_project, mock_provider):
    """Disabled agents are skipped without error."""
    state = tmp_project
    migration = state.load()
    migration["advisoryAgents"] = {"discovery-agent": False}
    state.save(migration)

    runner = AdvisoryAgentRunner(state)
    result = runner.run_agent(
        agent_yaml_path="advisory_agents/discovery-agent.yaml",
        input_data={"test": True},
        output_path="agents/test-output.json",
        task_instruction="Test",
    )
    assert result is None  # Skipped, not failed


def test_advisory_runner_refuses_non_advisory_agent(tmp_project, mock_provider):
    """Code-gen agents cannot be run through the advisory runner."""
    state = tmp_project
    runner = AdvisoryAgentRunner(state)
    result = runner.run_agent(
        agent_yaml_path="adapters/source/coldfusion/agents/cf-logic-agent.yaml",
        input_data={"test": True},
        output_path="agents/test-output.json",
        task_instruction="Test",
    )
    assert result is None  # Refused


def test_advisory_runner_retries_on_validation_failure(tmp_project, mock_provider):
    """Agent retries up to 3 times on schema validation failure."""
    # Mock provider returns invalid JSON first, then valid
    mock_provider.set_responses([
        '{"invalid": "schema"}',  # attempt 1: fails validation
        '{"invalid": "schema"}',  # attempt 2: fails validation
        '{"businessRules": [], "crossModulePatterns": [], "implicitRules": [], "deadCode": [], "gapFlags": []}',  # attempt 3: passes
    ])

    state = tmp_project
    runner = AdvisoryAgentRunner(state)
    result = runner.run_agent(
        agent_yaml_path="advisory_agents/discovery-agent.yaml",
        input_data={"test": True},
        output_path="agents/test-output.json",
        task_instruction="Test",
    )
    assert result is not None
    assert mock_provider.call_count == 3


def test_advisory_runner_writes_to_agents_dir(tmp_project, mock_provider):
    """Output is written to .modernize/agents/, not elsewhere."""
    mock_provider.set_response('{"businessRules": [], "crossModulePatterns": [], "implicitRules": [], "deadCode": [], "gapFlags": []}')

    state = tmp_project
    runner = AdvisoryAgentRunner(state)
    runner.run_agent(
        agent_yaml_path="advisory_agents/discovery-agent.yaml",
        input_data={"test": True},
        output_path="agents/discovery-report.json",
        task_instruction="Test",
    )

    assert (state.modernize_dir / "agents" / "discovery-report.json").exists()


def test_advisory_runner_logs_audit(tmp_project, mock_provider):
    """Every advisory agent run is logged in the audit trail."""
    mock_provider.set_response('{"businessRules": [], "crossModulePatterns": [], "implicitRules": [], "deadCode": [], "gapFlags": []}')

    state = tmp_project
    runner = AdvisoryAgentRunner(state)
    runner.run_agent(
        agent_yaml_path="advisory_agents/discovery-agent.yaml",
        input_data={"test": True},
        output_path="agents/discovery-report.json",
        task_instruction="Test",
    )

    # Check audit entries
    audit_entries = sorted((state.modernize_dir / "audit" / "entries").glob("*.json"))
    assert len(audit_entries) > 0
    entry = json.loads(audit_entries[-1].read_text())
    assert entry["action"] == "ai_call"
    assert "advisory:discovery-agent" in entry["details"]["stage"]
```

### 14.2 Unit Tests for Each Agent

File: `app/tests/unit/test_discovery.py`

```python
def test_discovery_report_from_dict():
    """DiscoveryReport round-trips through to_dict/from_dict."""
    report = DiscoveryReport(
        business_rules=[DiscoveredBusinessRule("UserService", "authenticate", "User Auth", "Validates creds", 92)],
        cross_module_patterns=[CrossModulePattern("Dup Auth", ["A", "B"], "Same check", "Consolidate")],
        implicit_rules=[ImplicitRule("UserService", "authenticate", "Lockout", "Locks after 3", "line 45", 74)],
        dead_code=[DeadCodeEntry("UserService", "legacyReset", "No callers")],
        gap_flags=[GapFlag("ReportService", "genMonthly", "businessRule", "Ask developer")],
    )
    d = report.to_dict()
    restored = DiscoveryReport.from_dict(d)
    assert len(restored.business_rules) == 1
    assert restored.business_rules[0].confidence == 92
    assert len(restored.cross_module_patterns) == 1
    assert len(restored.gap_flags) == 1


def test_discovery_skips_when_no_semantics(tmp_project):
    """Discovery Agent returns None when no semantic models exist."""
    from advisory.discovery import run_discovery
    result = run_discovery(tmp_project)
    assert result is None
```

File: `app/tests/unit/test_review_prioritizer.py`

```python
def test_review_checklist_from_dict():
    """ReviewChecklist round-trips through to_dict/from_dict."""
    checklist = ReviewChecklist(
        checklist=[ReviewChecklistItem(1, "CRITICAL", "UserService", "authenticate",
                                       "implicitRule", "Locks after 3", "Confirm lockout?",
                                       "AI confidence 74%, session writes")],
        summary=ReviewChecklistSummary(1, 1, 0, 0, 0, 30),
    )
    d = checklist.to_dict()
    restored = ReviewChecklist.from_dict(d)
    assert len(restored.checklist) == 1
    assert restored.summary.critical_count == 1
```

File: `app/tests/unit/test_arch_contradiction.py`

```python
def test_arch_contradiction_report_from_dict():
    """ArchContradictionReport round-trips through to_dict/from_dict."""
    report = ArchContradictionReport(
        contradictions=[ArchContradiction(
            contradiction_type="shared-table",
            severity="BLOCKING",
            services=["users-service", "audit-service"],
            description="Both write to users table",
            evidence=ContradictionEvidence(["UserService", "AuditLogger"], "Both UPDATE users"),
            resolution=ContradictionResolution("ownership", "Split the table"),
        )],
        blocking_count=1,
        warning_count=0,
        approval_recommendation="revise-and-resubmit",
    )
    d = report.to_dict()
    restored = ArchContradictionReport.from_dict(d)
    assert len(restored.contradictions) == 1
    assert restored.blocking_count == 1
    assert restored.approval_recommendation == "revise-and-resubmit"
```

File: `app/tests/unit/test_migration_risk.py`

```python
def test_migration_risk_dashboard_from_dict():
    """MigrationRiskDashboard round-trips through to_dict/from_dict."""
    dashboard = MigrationRiskDashboard(
        service_groups=[ServiceGroupRisk(
            name="users-service", risk_score=62, risk_level="MEDIUM",
            dimensions=RiskDimensions(45, 85, 30, 70, 55, 40),
            top_risks=["High data sensitivity", "Session-to-JWT migration"],
            mitigations=["Run security audit", "Prioritize auth flow testing"],
        )],
        recommended_sequence=["static-service", "users-service"],
        executive_summary="2 service groups identified.",
    )
    d = dashboard.to_dict()
    restored = MigrationRiskDashboard.from_dict(d)
    assert len(restored.service_groups) == 1
    assert restored.service_groups[0].risk_score == 62
    assert restored.recommended_sequence == ["static-service", "users-service"]


def test_migration_risk_markdown_generation():
    """Markdown report is generated correctly."""
    from advisory.migration_risk import _generate_markdown_report
    dashboard = MigrationRiskDashboard(
        service_groups=[ServiceGroupRisk(
            name="users-service", risk_score=62, risk_level="MEDIUM",
            dimensions=RiskDimensions(45, 85, 30, 70, 55, 40),
            top_risks=["High data sensitivity"],
            mitigations=["Run security audit"],
        )],
        recommended_sequence=["users-service"],
        executive_summary="1 service group.",
    )
    md = _generate_markdown_report(dashboard)
    assert "# Migration Risk Assessment" in md
    assert "users-service" in md
    assert "62/100" in md
```

File: `app/tests/unit/test_security_audit.py`

```python
def test_security_audit_report_from_dict():
    """SecurityAuditReport round-trips through to_dict/from_dict."""
    report = SecurityAuditReport(
        findings=[SecurityFinding("HIGH", "auth-drift", "user_handler.go", "45-52",
                                   "Missing JWT claim", "Locked stateWrites: session.userPermissions",
                                   "Add userPermissions to JWT claims")],
        critical_count=0, high_count=1, medium_count=0, low_count=0,
        pass_rate=89, approval_recommendation="approve-with-fixes",
    )
    d = report.to_dict()
    restored = SecurityAuditReport.from_dict(d)
    assert len(restored.findings) == 1
    assert restored.pass_rate == 89
```

File: `app/tests/unit/test_test_generation.py`

```python
def test_test_manifest_from_dict():
    """TestManifest round-trips through to_dict/from_dict."""
    manifest = TestManifest(
        test_files=[GeneratedTestFile("test-suite-supplement_test.go", "go", 24, 14, 10)],
        coverage=TestCoverage(18, 22, 81.8),
    )
    d = manifest.to_dict()
    restored = TestManifest.from_dict(d)
    assert len(restored.test_files) == 1
    assert restored.coverage.coverage_percent == 81.8
```

### 14.3 Integration Tests

File: `app/tests/integration/test_advisory_pipeline.py`

```python
def test_discovery_runs_after_extraction(tmp_project_with_semantics, mock_provider):
    """Discovery Agent runs automatically after extraction completes."""
    mock_provider.set_response(json.dumps({
        "businessRules": [{"module": "UserService", "function": "authenticate",
                           "name": "Auth", "description": "Validates", "confidence": 90}],
        "crossModulePatterns": [],
        "implicitRules": [],
        "deadCode": [],
        "gapFlags": [],
    }))

    from pipeline.extractor import run_extract
    run_extract(tmp_project_with_semantics)

    # Discovery report should exist
    report = tmp_project_with_semantics.read_artifact("agents", "discovery-report.json")
    assert report is not None
    assert len(report["businessRules"]) == 1


def test_contradiction_detector_runs_after_architect(tmp_project_with_lock, mock_provider):
    """Arch Contradiction Detector runs after target architecture design."""
    mock_provider.set_response(json.dumps({
        "contradictions": [],
        "summary": {"blockingCount": 0, "warningCount": 0, "approvalRecommendation": "approve"},
    }))

    from pipeline.architect import run_architect_target
    run_architect_target(tmp_project_with_lock)

    report = tmp_project_with_lock.read_artifact("agents", "arch-contradictions.json")
    assert report is not None


def test_pipeline_continues_when_agent_fails(tmp_project_with_semantics, mock_provider):
    """Pipeline continues even when advisory agent fails."""
    mock_provider.set_error(ProviderError("test", "API down"))

    from pipeline.extractor import run_extract
    # Should NOT raise — agent failure is non-blocking
    run_extract(tmp_project_with_semantics)

    # Extraction should have completed (semantics written)
    assert len(tmp_project_with_semantics.list_artifacts("semantics", ".semantic.json")) > 0

    # Discovery report should NOT exist (agent failed)
    report = tmp_project_with_semantics.read_artifact("agents", "discovery-report.json")
    assert report is None


def test_disabled_agents_not_called(tmp_project_with_semantics, mock_provider):
    """Disabled agents are not invoked."""
    migration = tmp_project_with_semantics.load()
    migration["advisoryAgents"] = {"discovery-agent": False}
    tmp_project_with_semantics.save(migration)

    from pipeline.extractor import run_extract
    run_extract(tmp_project_with_semantics)

    # Provider should NOT have been called for discovery
    assert mock_provider.call_count == 0  # Only code-gen calls, no advisory
```

### 14.4 Test Fixtures

File: `app/tests/fixtures/advisory/sample_semantic_model.json`

```json
{
  "module": "UserService",
  "source": "UserService.cfc",
  "functions": [
    {
      "name": "authenticate",
      "signature": {
        "inputs": [{"name": "email", "type": "string"}, {"name": "password", "type": "string"}],
        "outputs": {"type": "struct", "keys": ["id", "email", "role"]}
      },
      "businessRule": {
        "name": "User Authentication",
        "description": "Validates credentials against stored hash",
        "source": "ai",
        "confidence": 92
      },
      "dataAccess": [
        {"table": "users", "operation": "SELECT", "columns": ["id", "email", "password_hash", "role"],
         "filter": "email = ?", "parameterized": true}
      ],
      "stateWrites": [
        {"scope": "session", "key": "userId"},
        {"scope": "session", "key": "userRole"},
        {"scope": "session", "key": "userPermissions"}
      ],
      "controlFlow": [
        {"condition": "no user found", "action": "throw InvalidCredentials"},
        {"condition": "password mismatch", "action": "throw InvalidCredentials"},
        {"condition": "3 failed attempts", "action": "lock account for 30 minutes"}
      ],
      "calls": ["SessionService.createSession"],
      "calledBy": ["LoginController.handleLogin", "APIGateway.authenticate"]
    }
  ],
  "dependencies": ["SessionService"],
  "tables": ["users"],
  "complexity": "medium"
}
```

---

## 15. Implementation Order

### Phase A: Advisory Infrastructure (implement first)

1. **Data models** — Add all v3 dataclasses to `core/models.py` (Section 4)
2. **Advisory runner** — `advisory/__init__.py` + `advisory/runner.py` (Section 5.1)
3. **Registry updates** — Add `get_advisory_agents()`, `get_advisory_for_stage()` to `agents/registry.py` (Section 5.3)
4. **State update** — Add `agents/` to `ProjectState.init()` mkdir list (Section 5.4)
5. **Migration.json update** — Add `advisoryAgents` config field (Section 5.5)
6. **Tests** — `test_advisory_runner.py` (Section 14.1)

### Phase B: Discovery + Review Prioritizer (Phase 2 agents)

7. **Discovery Agent YAML** — `advisory_agents/discovery-agent.yaml` (Section 6.1)
8. **Discovery Agent logic** — `advisory/discovery.py` (Section 6.2)
9. **Review Prioritizer YAML** — `advisory_agents/review-prioritizer-agent.yaml` (Section 7.1)
10. **Review Prioritizer logic** — `advisory/review_prioritizer.py` (Section 7.2)
11. **Pipeline hooks** — Add hooks to `pipeline/extractor.py` and `pipeline/documenter.py` (Sections 12.1, 12.2)
12. **CLI** — `modernize agents discovery-report`, `modernize agents review-checklist`, update `review semantics --prioritized` (Sections 13.2, 13.4)
13. **Tests** — `test_discovery.py`, `test_review_prioritizer.py` (Section 14.2)

### Phase C: Architecture Contradiction + Migration Risk (Phase 3 agents)

14. **Arch Contradiction YAML** — `advisory_agents/arch-contradiction-agent.yaml` (Section 8.1)
15. **Arch Contradiction logic** — `advisory/arch_contradiction.py` (Section 8.2)
16. **Migration Risk YAML** — `advisory_agents/migration-risk-agent.yaml` (Section 9.1)
17. **Migration Risk logic** — `advisory/migration_risk.py` (Section 9.2)
18. **Pipeline hooks** — Add hooks to `pipeline/architect.py` and `pipeline/generator.py` (Sections 12.3, 12.4)
19. **CLI** — `modernize agents arch-contradictions`, `modernize agents risk-dashboard` (Section 13.2)
20. **Tests** — `test_arch_contradiction.py`, `test_migration_risk.py` (Section 14.2)

### Phase D: Security Audit + Test Generation (Phase 5 agents)

21. **Security Audit YAML** — `advisory_agents/security-audit-agent.yaml` (Section 10.1)
22. **Security Audit logic** — `advisory/security_audit.py` (Section 10.2)
23. **Test Generation YAML** — `advisory_agents/test-generation-agent.yaml` (Section 11.1)
24. **Test Generation logic** — `advisory/test_generation.py` (Section 11.2)
25. **Pipeline hooks** — Add hooks to `pipeline/generator.py` (post) and `pipeline/verifier.py` (Sections 12.4, 12.5)
26. **CLI** — `modernize agents security-audit <service>`, `modernize agents generate-tests <service>`, `modernize agents test-coverage <service>` (Section 13.2)
27. **Tests** — `test_security_audit.py`, `test_test_generation.py` (Section 14.2)

### Phase E: Configuration + Polish

28. **Agent config CLI** — `modernize agents list`, `modernize agents disable`, `modernize agents enable` (Section 13.3)
29. **Integration tests** — `test_advisory_pipeline.py` (Section 14.3)
30. **Architecture review update** — Show contradictions in `review architect` (Section 12.7)
31. **Code review update** — Show security audit in `review generate` (Section 13.4)

---

## Appendix A: Advisory Agent Write Isolation Enforcement

The `AdvisoryAgentRunner.run_agent()` method enforces write isolation:

```python
# In run_agent(), after computing output_full_path:
agents_dir = self.state.modernize_dir / "agents"
if not str(output_full_path.resolve()).startswith(str(agents_dir.resolve())):
    console.print(f"[red]BLOCKED: Advisory agent tried to write outside agents/ directory: {output_path}[/]")
    return None
```

This prevents a malformed agent YAML from writing to `locked/`, `semantics/`, or `services/`.

---

## Appendix B: Advisory Agent Execution Flow Summary

```
Pipeline Stage          Advisory Agent              Trigger
─────────────          ──────────────              ───────
Step 2: Extract    →   Discovery Agent              After all extractions + consistency check
Step 3: Document   →   Review Prioritizer Agent     After doc generation
Step 5d: Design    →   Arch Contradiction Agent     After target architecture design
Pre-Step 6         →   Migration Risk Agent         Once, before first service generation
Step 6: Generate   →   Security Audit Agent         After each service group generation
Step 7: Verify     →   Test Generation Agent        At start of verification per service
```

All agents are:
- **Non-blocking**: Pipeline continues on agent failure
- **Write-isolated**: Can only write to `.modernize/agents/`
- **Audited**: Every run logged in `.modernize/audit/`
- **Optional**: Individually disableable via `modernize config agents --disable <name>`
- **Cost-tracked**: All AI calls counted toward budget

---

## Appendix C: CLI Command Reference (v3 Additions)

```
# Advisory agent reports
modernize agents discovery-report
modernize agents review-checklist
modernize agents arch-contradictions
modernize agents risk-dashboard
modernize agents security-audit <service>
modernize agents generate-tests <service>
modernize agents test-coverage <service>

# Advisory agent management
modernize agents list
modernize agents disable <agent-name>
modernize agents enable <agent-name>

# Updated v2 commands with advisory integration
modernize review semantics [--prioritized]        # Shows CRITICAL+HIGH from checklist
modernize review architect                        # Shows contradiction warnings
modernize review generate <service>               # Shows security audit summary
```
