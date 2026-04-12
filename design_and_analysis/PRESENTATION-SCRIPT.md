# Modernize Pipeline — Presentation Script
**Duration: 15–20 minutes | 24 steps (0–23)**

Use arrow keys or the Next button to advance. Each section below tells you what's on screen and what to say.

---

## Step 0 — Project Objective (~1 min)

**On screen:** Full-screen card — "Modernize legacy applications through a governed, repeatable pipeline."

**Say:**

> The goal is straightforward: take legacy applications and modernize them through a pipeline that's governed, repeatable, and stack-agnostic. It's not tied to any one language — the current engagement happens to be ColdFusion, but the approach works for COBOL, classic ASP, legacy Java, anything.
>
> Two key principles: the pipeline is generic by design, and we preserve business logic with evidence — not guesswork.

---

## Step 1 — Current Approach (~2 min) ★ KEY SLIDE

**On screen:** Full-screen card — 5 challenges with orange indicators.

**Say:**

> Before I walk through the proposed pipeline, let me frame where we are today. The current approach has hit real constraints:
>
> **AI hallucination** — ColdFusion source was fed directly to AI. The output was hallucinated documentation. The output required significant rework.
>
> **Manual extraction** — Business rules had to be captured through multiple in-person sessions with the original developers.
>
> **Slow doc generation** — Code entry points were manually identified, then AI was prompted one file at a time. Over 200 files generated this way. Fragile, slow process.
>
> **Limited developer access** — Institutional knowledge is concentrated in very few original developers. Availability is a bottleneck.
>
> **Constrained AI environment** — The client is restricted to Azure Cloud Foundry models, which aren't sufficient for reliable code understanding at this scale.
>
> The current state: source architecture has been approved, but there's no target architecture yet. The question is — *what if we had a governed pipeline from day one?*

**[ADVANCE — pipeline appears]**

---

## Step 2 — Control Surface (~30 sec)

**On screen:** CLI terminal with `modernize status`, `modernize run`, `modernize resume`, `modernize estimate`.

**Say:**

> Everything starts at the CLI. Operators drive the pipeline through a single control surface. You can check status, run specific stages, resume from checkpoints if something fails, and estimate cost before committing to an AI-heavy stage. This gives the team full visibility and control.

---

## Step 3 — Source + Config Discovery (~30 sec)

**On screen:** Discovery scan results — file counts, config detection, environment inputs.

**Say:**

> The pipeline begins by scanning the entire source estate. It inventories every file type, detects configuration files, identifies the runtime environment. Nothing is processed until everything is inventoried. This is fully deterministic — no AI needed here.

---

## Step 4 — Legacy System Input (~20 sec)

**On screen:** Estate card.

**Say:**

> The legacy system feeds into the pipeline as a structured input — source code, database schemas, configuration. This is the "as-is" that everything downstream builds on.

---

## Step 5 — Source Adapters (~1 min) ★ KEY SLIDE

**On screen:** Adapters visual + "Previously" callout.

> **Previously callout:** *"Client environment limited to Azure Cloud Foundry AI models — insufficient for reliable ColdFusion parsing. Deterministic adapters eliminate this dependency entirely."*

**Say:**

> This is where the architecture makes a critical choice. Source adapters are **deterministic** — they use language-specific parsers, not AI. For ColdFusion, we wrote a parser that understands CFM, CFC, SQL files natively.
>
> Why does this matter? Look at the "Previously" note. The client's AI environment couldn't reliably parse ColdFusion. By making this step deterministic, we remove that dependency entirely. The adapters work regardless of what AI models are available.

---

## Step 6 — AST and Facts (~1 min) ★ KEY SLIDE

**On screen:** AST facts visual + "Previously" callout.

> **Previously callout:** *"AI interpreted raw ColdFusion source directly — hallucinated documentation that the client rejected."*

**Say:**

> The adapters produce an Abstract Syntax Tree and a structured fact base. Function signatures, data flows, SQL queries, file dependencies — all extracted deterministically.
>
> This is the direct answer to the hallucination problem. Instead of asking AI to understand raw source code — which produced rejected output — we give AI **structured facts**. The AI never sees raw ColdFusion. It sees typed, validated data structures. That's why the downstream AI steps work reliably.

---

## Step 7 — Semantic Derivation (~1.5 min) ★ KEY SLIDE

**On screen:** Semantic derivation visual + "Previously" callout. Purple "AI Heavy" badge visible.

> **Previously callout:** *"Business rules extracted through multiple manual sessions with original developers."*

**Say:**

> This is the first AI-heavy step — and one of the most valuable. The AI reads the structured facts and derives business rules, validation logic, workflow sequences.
>
> Critically, every derived rule comes with a **confidence score** and **evidence pointers** back to the AST. If the AI says "there's a 15% discount rule for orders over $500," it points to the exact function, line, and SQL query that supports it.
>
> Compare that to the current approach: multiple manual sessions with the original developers, no confidence scoring, no evidence chain. The pipeline captures what took weeks of interviews and does it with traceable evidence.

---

## Step 8 — Semantic Review (~1 min) ★ KEY SLIDE

**On screen:** Review visual + "Previously" callout. Teal "Human+AI" badge.

> **Previously callout:** *"Reviewers saw everything with equal priority."*

**Say:**

> This is a human approval gate — but it's an *intelligent* one. Items are sorted by confidence. Low-confidence items surface first so that expensive developer time goes to what actually needs human judgment.
>
> Previously, reviewers saw everything with equal priority. A routine getter function got the same attention as a complex discount calculation. Now the pipeline prioritizes automatically.

---

## Step 9 — Semantic Lock (~30 sec)

**On screen:** Lock certificate visual.

**Say:**

> Once semantics are approved, they're locked with a certificate. The lock has a hash, a timestamp, and an approver. Nothing downstream can modify locked semantics without going through the review gate again. This is the governance backbone.

---

## Step 10 — Source Architecture (~1 min) ★ KEY SLIDE

**On screen:** Source architecture visual + "Previously" callout.

> **Previously callout:** *"Architecture docs generated one at a time — manually identifying code entry points, then prompting AI per file."*

**Say:**

> The pipeline generates the source architecture from locked semantics, but this is where we need to be precise: diagrams alone are not enough for a large estate.
>
> For complex systems, a single Mermaid diagram becomes unreadable. So the output is a review pack: high-level architecture views, focused hotspot views, sequence flows for critical journeys, and a generated business requirements pack derived from the same locked understanding.
>
> Previously, this was 200+ files generated one at a time by manually identifying code entry points and prompting AI per file. No versioning, no invalidation tracking. Here, if a semantic rule changes, the pipeline knows exactly which architecture views and which requirement documents are stale.

---

## Step 11 — Source Architecture Review (~20 sec)

**Say:**

> Another human review gate. The diagrams help reviewers orient themselves, but the main thing they review is the generated business requirements: what the system does, what rules it enforces, and where the open questions are.
>
> That is the strong review surface, because stakeholders can revise requirements directly while still having traceability back to the semantics and architecture evidence.

---

## Step 12 — Source Architecture Lock (~20 sec)

**Say:**

> Once approved, the source architecture and the reviewed business requirements become the locked, versioned baseline. The "as-is" is now captured in both structural and business terms, and both are governed.

---

## Step 13 — Target Stack Choice (~30 sec)

**On screen:** Target stack selection visual.

**Say:**

> This is a human decision point. The team selects the target technology stack. The pipeline provides the information — module complexity, dependency patterns, integration points — but the technology choice is a human call.

---

## Step 14 — Target Architecture (~45 sec)

**On screen:** Target architecture visual. Purple "AI Heavy" badge.

**Say:**

> Given the locked source architecture, the reviewed business requirements, and the chosen target stack, the AI generates the target architecture. It maps source modules to target services, proposes API boundaries, and designs the data migration strategy.
>
> Because it's working from locked, verified inputs — not raw source — the output is grounded and traceable.

---

## Step 15 — Architecture Review (~20 sec)

**Say:**

> Human review of the target architecture. This is where the team validates the AI's architectural proposals before any code gets generated.

---

## Step 16 — Architecture Lock (~20 sec)

**Say:**

> Target architecture locked. We now have both the "as-is" and the "to-be" locked and governed. Everything needed for generation is frozen.

---

## Step 17 — Generation (~45 sec)

**On screen:** Generation visual. Purple "AI Heavy" badge.

**Say:**

> Code generation works from two locked inputs: source architecture and target architecture. The generator uses target-specific adapters — so a Go adapter produces idiomatic Go, a Java adapter produces idiomatic Java.
>
> Every generated file carries metadata: which lock certificates it was built from, which generator version, which adapter. If anything upstream changes, you know exactly what to regenerate.

---

## Step 18 — Generated Outputs (~30 sec)

**On screen:** Generation metadata visual.

**Say:**

> The outputs include the generated code plus full metadata — lock references, generator version, per-file output hashes. This metadata enables safe regeneration. If you need to rerun generation after a lock update, the pipeline knows exactly what changed.

---

## Step 19 — Verification (~45 sec)

**On screen:** Behavioral verification visual — legacy vs target comparison.

**Say:**

> Verification compares the generated target against locked semantics and the approved business requirements — not just syntax, but behavior. The pipeline runs scenarios and classifies results as pass, acceptable drift, or failure. In this example, an auth session mismatch is caught: legacy uses cookies, target returns JWT only. That's a real behavioral difference that needs resolution.

---

## Step 20 — Verification Reports (~30 sec)

**On screen:** Verification report with verdict, scores, blocking items.

**Say:**

> Verification produces a formal report: pass rate, drift classification, and blocking items. This is the release gate. The team gets actionable evidence, not just a green/red signal.

---

## Step 21 — Cutover Support (~30 sec)

**On screen:** Gateway/proxy diagram with gradual traffic shift.

**Say:**

> The pipeline provides cutover support — routing templates, rollback checklists, verification during gradual traffic shift. The actual cutover is engagement-specific, but the framework gives you the scaffolding.

---

## Step 22 — Cross-Cutting Concerns (~45 sec)

**On screen:** Four horizontal bars — State Store, Audit Log, Invalidation Engine, Advisory Agents.

**Say:**

> Four cross-cutting concerns span the entire pipeline:
>
> **State store** — checkpoints and recovery at every stage. If something fails, you resume, not restart.
>
> **Audit log** — every AI call, every decision, every hash in a tamper-evident chain. Full accountability.
>
> **Invalidation engine** — if source changes, stale artifacts cascade automatically. No manual tracking.
>
> **Advisory agents** — optional. They suggest tests, flag risks, help with reviews. But the core pipeline works without them. They accelerate; they don't gate.

---

## Step 23 — Evolution: Agent Layer (~1.5 min) ★ CLOSING SLIDE

**On screen:** Purple dashed agent envelopes overlay the pipeline. Side panel shows 3 consolidated agents.

**Say:**

> This is the evolution path. Everything you've seen so far is the deterministic, governed pipeline — it works today. The next evolution wraps this pipeline in three AI agents.
>
> **Parse & Extract Agent** — supervises discovery, adapters, and AST extraction. On the happy path, the deterministic tools just work and the agent passes through. On exceptions — say, a file the parser doesn't recognize — the agent applies AI judgment to adapt.
>
> **Lock Guardian Agent** — supervises all three lock points: semantic, source architecture, and target architecture. It validates pre-conditions before freezing. If something doesn't look right, it flags it before the human reviewer even sees it.
>
> **Verification Agent** — interprets drift results, filters false positives, and escalates real issues. Reduces noise in verification reports.
>
> The key insight: **same pipeline, same locks, smarter execution**. The agents don't replace the governance — they enhance it. Deterministic on the happy path, AI judgment only on exceptions. Three agents supervising deterministic tools.

---

## Wrap-up (~30 sec)

> That's the full pipeline. It addresses every constraint we saw in the current approach: no more hallucinated docs, no more manual extraction sessions, no more one-at-a-time file generation, and no dependency on specific AI models for the core parsing work.
>
> The source architecture that took months is now governed, versioned, and reproducible. And the agent evolution path gives us a clear roadmap for increasing automation without sacrificing governance.
>
> More importantly, the review conversation shifts from "can anyone read this diagram?" to "are these business requirements correct?" That's the artifact stakeholders can actually revise with confidence.

---

## Timing Summary

| Section | Steps | Time |
|---------|-------|------|
| Intro (objective + current approach) | 0–1 | ~3 min |
| Pipeline entry (CLI, discovery, input) | 2–4 | ~1.5 min |
| Source processing (adapters → semantic lock) | 5–9 | ~4.5 min |
| Architecture (src arch → target lock) | 10–16 | ~3 min |
| Generation + verification | 17–20 | ~2.5 min |
| Cutover + cross-cutting | 21–22 | ~1.5 min |
| Agent evolution + wrap-up | 23 + close | ~2 min |
| **Total** | | **~18 min** |
