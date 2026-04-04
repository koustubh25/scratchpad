1. Risk 1 — AST complexity will explode faster than expected

This is the #1 technical risk.

Not performance.

Not AI.

AST coverage.

Especially for:

ColdFusion
COBOL
legacy Java
dynamic languages

The parser will be the hardest component.

Much harder than the AI.

**MITIGATION**
1) Cache AST aggressively

Never reparse unchanged files.

2) Normalize syntax early

Convert:

tags
script
HTML

Into:

unified AST model

3) Extract dependencies before semantics

Do not try to understand everything at once.

First build:

structure

Then build:

meaning

4) Process files independently

Avoid:

global parsing passes

5) Accept partial understanding

Do not block the pipeline because:

some constructs are unknown.

The biggest mindset shift

You are not building:

a perfect parser

You are building:

a resilient analysis system

If this were my system

I would implement:

Mandatory

AST cache
dependency graph
incremental pipeline

Optional

Neo4j

Critical

fallback parsing strategy

Bottom line

Your concern is valid.

But the solution is not:

better parsing

It is:

better system architecture around parsing

And yes — a graph database can be a powerful component, but:

it is an accelerator, not the foundation.

2. Risk 2 — semantic extraction will become the bottleneck

The extraction stage looks deterministic on paper.

In reality:

it will contain the most heuristics.

Examples:

implicit business rules
dynamic SQL
reflection
runtime configuration
framework magic

Expect this stage to grow significantly.

**MITIGATION**

First — what Risk 2 really means

Semantic extraction bottleneck = turning syntax into behavior.

Not:

parsing code
building AST
generating new code

But:

figuring out what the system actually does.

Example of the problem

You can parse this easily:

<cfquery name="qUser">
  SELECT * FROM users WHERE id = #url.id#
</cfquery>

But semantics require answering:

Which endpoint calls this?
What table is affected?
Is url.id validated?
Is this read or write?
Is this security-sensitive?
Does it affect business rules?

That’s semantic extraction.

Why semantic extraction becomes the bottleneck

These are the four real causes — not theory, but what happens in legacy ColdFusion systems.

1) Hidden business logic in infrastructure code

Typical pattern:

if (session.userRole EQ "admin") {
   allowDelete = true
}

This is:

authorization logic

But it lives:

inside controller code

Not:

in an auth module

So the system must infer:

DELETE permission requires admin role
2) Dynamic SQL and string construction

Example:

sql = "SELECT * FROM " & tableName

Static parsing sees:

string concatenation

Semantics require:

identifying database dependencies

3) Implicit framework behavior

ColdFusion has:

Application.cfc lifecycle
scopes (request/session/application)
implicit routing
ORM mapping
configuration inheritance

These create:

dependencies that do not exist in code.

4) Runtime configuration drives behavior

Example:

if (application.enableFeatureX) {
   runNewLogic()
}

This means:

behavior depends on environment state.

The real risk

The pipeline slows down because:

You cannot extract meaning deterministically.

Not because:

The system is slow.

The key mitigation principle

You do not need perfect semantics.

You need:

progressive semantics.

Progressive semantics model

Think in levels.

Level 1 — Structural semantics

Extract:

functions
endpoints
database tables
API calls
file dependencies

No business meaning yet.

Level 2 — Behavioral semantics

Extract:

reads
writes
side effects
data flow
Level 3 — Business semantics

Extract:

business rules
permissions
workflows

Most systems fail because they try to jump directly to Level 3.

The most effective mitigation strategies

These are proven patterns.

Mitigation 1 — Treat semantics as a separate pipeline

Do not mix parsing and semantics.

Bad model
parse → understand everything
Correct model
parse → extract facts → derive meaning

Think:

compiler → static analyzer

Mitigation 2 — Build a "fact extraction" layer

Instead of:

trying to understand logic

Extract:

observable facts.

Example facts
Function: getUser
Reads: users table
Input: url.id
Output: query result

Not:

This function retrieves a user profile

Facts scale.

Interpretation does not.

Mitigation 3 — Use rule-based extraction before AI

This is critical.

Deterministic rules

Examples:

cfquery → database access

cfhttp → external API

session.* → user state

insert/update/delete → write operation

These rules cover:

70–80% of semantics.

Without AI.

AI should handle:

edge cases only.

Mitigation 4 — Build a semantic confidence system

Every extracted semantic must carry:

confidence.

Example
Dependency: users table
Confidence: 0.95

Business rule: admin required
Confidence: 0.60

This allows:

prioritized review.

Mitigation 5 — Make semantics incremental

Never recompute everything.

Instead of
re-extract semantics for 1000 files

Do

re-extract semantics for changed nodes only

This is where your earlier graph discussion becomes powerful.

Mitigation 6 — Externalize configuration

Do not rely on runtime state.

Build a configuration snapshot

Example:

application settings
feature flags
database mappings
environment variables

Store them as:

deterministic inputs.

Mitigation 7 — Introduce semantic contracts

Every component must declare:

what it does.

Example
Function: deleteUser

Contract:

Inputs:
  userId

Side effects:
  deletes row from users

Permissions:
  admin

This becomes:

testable behavior.

The architecture pattern that solves Risk 2
Semantic Extraction Architecture
AST
  ↓
Fact Extractors
  ↓
Fact Store
  ↓
Semantic Derivation
  ↓
Review
  ↓
Lock
Fact extraction modules

These are the core.

1) Database extractor

Detect:

SELECT
INSERT
UPDATE
DELETE

Output:

Table: users
Operation: READ
2) API extractor

Detect:

cfhttp
fetch
REST calls

Output:

External dependency: payment API
3) State extractor

Detect:

session
request
application

Output:

Uses session state
4) Routing extractor

Detect:

URL parameters
form inputs
endpoints

Output:

Endpoint: /users/{id}
This is the most important structural decision
Separate facts from meaning

Facts:

writes users table

Meaning:

creates user account

Only humans (or higher-level reasoning) should assign meaning.

Performance mitigation

These matter operationally.

1) Parallelize fact extraction

Safe because:

facts are local to files.

2) Cache semantic results

Never recompute unchanged files.

3) Use change detection
hash(file)

If unchanged:

skip extraction.

4) Store semantics in normalized form

Not text.

Structured data.

Example semantic record
Function:
   name: getUser

Dependencies:
   tables:
      - users

Operations:
   reads:
      - users

Inputs:
   - url.id

Confidence:
   0.92
Where systems usually fail

These are the three classic mistakes.

Mistake 1 — trying to infer business logic automatically

Do not do this.

Humans must validate business meaning.

Mistake 2 — treating semantics as static

Semantics evolve during migration.

Mistake 3 — blocking the pipeline on uncertainty

Never do this.

Use:

confidence thresholds instead.

How this applies directly to your 1000 ColdFusion files

Here is the realistic workflow.

Step 1 — Extract structural facts

For every file:

Identify:

functions
tables
APIs
state usage
Step 2 — Build dependency graph

Nodes:

functions
tables
endpoints

Edges:

reads
writes
calls
Step 3 — Assign confidence

Automatically.

Step 4 — Review only low-confidence items

Not everything.

Step 5 — Lock semantics

Freeze the model.

The single most powerful mitigation
Introduce a "Semantic Fact Store"

This becomes:

the memory of the system.

It stores:

who calls what
who reads what
who writes what

Not:

interpretation.

If this were my system

I would implement these first.

Mandatory

Fact extractors
Confidence scoring
Incremental semantics
Caching

Very high value

Dependency graph
Configuration snapshot

Optional

AI reasoning layer

The most important mindset shift

You are not building:

semantic understanding

You are building:

semantic evidence

Bottom line

Risk 2 is real, but manageable if you:

extract facts instead of meaning
make semantics incremental
track confidence
separate behavior from interpretation

Do those four things, and semantic extraction will scale — even for large ColdFusion systems.

3. Risk 3 — human review scalability

Your design assumes:

original developers review semantics

In many real projects:

they are unavailable.

Or gone.

Or overloaded.

You will need fallback workflows.

**MITIGATION**

First — what Risk 3 really is

Human review scalability risk = review demand grows faster than reviewer capacity.

Not:

lack of people
lack of expertise

But:

too many review decisions per unit time

The real failure mode

Most systems assume:

Every artifact must be reviewed.

That does not scale.

Instead, you need:

Only risky artifacts must be reviewed.

The math of the problem

Let’s quantify your case.

Without mitigation

Assume:

1000 files
10 semantic items per file
5 minutes per review

That becomes:

1000 × 10 × 5 minutes
= 50,000 minutes
= 833 hours
= ~21 weeks full-time

That’s the bottleneck.

With proper mitigation

Review:

only low-confidence items
only high-impact changes

You get:

~5–10% review load.

That’s the difference between:

project success
and project stall.

The core insight

You don’t scale humans.

You scale:

review selection.

The 5 root causes of review scalability problems

These show up in almost every modernization project.

1) Review scope is too broad

Example:

Review every function.

Instead of:

Review only risky functions.

2) Review context is missing

Reviewers must:

read code
understand system
infer behavior

This is slow.

3) Reviews are binary

Approve / Reject.

Instead of:

confidence scoring.

4) Review workflows are synchronous

Pipeline waits.

Instead of:

asynchronous review queues.

5) Review effort is not prioritized

Everything is treated equally.

Instead of:

risk-based prioritization.

The architectural solution
Risk-Based Review System
Artifacts
   ↓
Risk Scoring
   ↓
Review Queue
   ↓
Human Review
   ↓
Lock
The single most important mitigation
Introduce Risk Scoring

Every artifact gets:

{
  "confidence": 0.82,
  "impact": "HIGH",
  "complexity": "MEDIUM",
  "risk": 0.41
}

Review is triggered only when:

risk > threshold
Risk scoring model

Use three dimensions.

1) Confidence

How sure the system is.

Examples:

static SQL → high confidence
dynamic SQL → low confidence
2) Impact

What happens if this is wrong.

Examples:

High impact:

payments
authentication
data writes

Low impact:

logging
formatting
reporting
3) Complexity

How hard the logic is.

Examples:

High complexity:

nested conditions
dynamic includes
reflection

Low complexity:

simple CRUD
Risk formula

Simple and effective:

risk = impact × complexity × (1 - confidence)

You don’t need ML.

Mitigation 1 — Confidence-based auto-approval

Most artifacts should never reach humans.

Example rule

If:

confidence ≥ 0.9
impact = LOW

Then:

auto-lock

This alone reduces review load dramatically.

Mitigation 2 — Tiered review system

Not all reviews require the same expertise.

Tier 1 — Automated review

Checks:

schema validation
dependency consistency
naming conventions
Tier 2 — Technical review

Performed by:

engineer

Checks:

correctness
dependencies
Tier 3 — Business review

Performed by:

domain expert

Checks:

behavior
rules

Only Tier 3 is expensive.

You want:

as few Tier 3 reviews as possible.

Mitigation 3 — Review summaries instead of raw artifacts

Never show:

AST
code

Show:

structured summaries.

Example summary
Function: deleteUser

Changes:

Writes:
  users table

Conditions:
  requires admin role

Confidence:
  0.78

Risk:
  HIGH

This reduces:

review time by 5–10x.

Mitigation 4 — Batch reviews

Humans review groups, not items.

Instead of

Review:

Function A
Function B
Function C
Do

Review:

Module: User Management

Changes:

3 functions write to users table
2 functions read session state

This scales much better.

Mitigation 5 — Progressive locking

Do not lock everything immediately.

Lock levels
DRAFT
REVIEWED
LOCKED
FINAL

Most artifacts stay:

REVIEWED

Only critical ones become:

LOCKED

Mitigation 6 — Review queues

Do not block the pipeline.

Instead of
pipeline waits for review
Use
pipeline continues
review happens asynchronously

This is how CI/CD works.

Mitigation 7 — Review reuse

One of the most powerful techniques.

If:

same pattern appears 50 times

Review:

once.

Apply:

everywhere.

Example
<cfquery>
  SELECT * FROM users WHERE id = ?
</cfquery>

After first approval:

All identical queries:

auto-approved.

Mitigation 8 — Visual dependency context

Reviewers need context.

Not code.

This is where your earlier graph discussion becomes critical.

Instead of:

reading files

Show:

deleteUser
   ├── writes → users
   ├── requires → admin
   └── called by → UserController

Review becomes:

seconds instead of minutes.

Mitigation 9 — Review sampling

For low-risk systems.

Example:

Review:

10%

Auto-approve:

90%

This is used in:

data pipelines
financial audits
large migrations

Mitigation 10 — Reviewer memory

Store decisions.

If a reviewer approves:

pattern: safe SQL read

Future matches:

auto-approved.

This turns:

human knowledge

into:

system policy.

The architecture pattern that solves Risk 3
Human-Scalable Review Architecture
Artifacts
   ↓
Risk Scoring
   ↓
Auto-Approval
   ↓
Review Queue
   ↓
Batch Review
   ↓
Decision Memory
   ↓
Lock
Minimal implementation for your system

You do not need a large system.

Start simple.

Step 1 — Add confidence to every artifact

Mandatory.

Step 2 — Define risk thresholds

Example:

risk < 0.2 → auto-approve
risk 0.2–0.5 → technical review
risk > 0.5 → business review
Step 3 — Build review summaries

Mandatory.

Step 4 — Add batch review

High value.

Step 5 — Store reviewer decisions

Very high value.

Realistic scaling for your 1000-file system
Without mitigation

You need:

weeks of review.

With mitigation

You need:

days.

Typical distribution:

70% auto-approved
20% technical review
10% business review
The most important design decision
Reviews should validate risk — not correctness.

Correctness is:

system responsibility.

Risk validation is:

human responsibility.

If this were my system

I would implement these first.

Mandatory

Confidence scoring
Risk scoring
Auto-approval rules
Review summaries

Very high value

Batch reviews
Decision memory
Review queues

Optional

Sampling
ML risk prediction

4. Risk 4 — architecture synthesis is underspecified

This step:

Design target architecture

is the hardest design problem in the system.

Not code generation.

Not parsing.

Architecture decisions are:

contextual
organizational
political

You correctly require human review, but:

the heuristics need more definition.

**MITIGATION**

First — what Risk 4 really is

Architecture synthesis risk = too many design choices with insufficient constraints.

Not:

lack of tools
lack of code
lack of AI

But:

lack of deterministic decision rules for system design

The real failure mode

Most modernization systems assume:

“We will generate the target architecture.”

But architecture is not generated — it is selected from constrained options.

If you don’t constrain it, you get:

endless design debates
inconsistent services
rework cycles
stakeholder friction
Why this risk is especially relevant to your scenario

You are likely moving from:

ColdFusion monolith
→ modern service-based system (e.g., Go, Python, Node, etc.)

That transition forces decisions about:

service boundaries
database ownership
API contracts
state management
deployment model

These are architectural decisions, not code generation tasks.

The core insight

You don’t synthesize architecture from code.

You synthesize architecture from:

policies + constraints + system behavior

The 5 root causes of architecture synthesis problems
1) Service boundaries are ambiguous

Example:

One ColdFusion file may:

read users
update orders
send emails

So:

Is it:

UserService
OrderService
NotificationService
2) Target architecture is undefined

If you don’t specify:

monolith
modular monolith
microservices

Then every module becomes a debate.

3) Non-functional requirements are missing

Architecture depends heavily on:

performance
latency
reliability
deployment constraints
team size

Without these, decisions are arbitrary.

4) Data ownership is unclear

This is the biggest practical blocker.

Example:

Multiple modules write to the same table.

Now:

Who owns the data?

5) Technology choices drive architecture unintentionally

Example:

Choosing Kubernetes too early can force:

microservices

Even when:

a modular monolith is better.

The architectural mitigation principle

You don’t design architecture dynamically.

You define:

Architecture Policies

Then derive structure deterministically.

The single most important mitigation
Introduce an Architecture Policy Layer

This becomes:

the rulebook for system design.

Example policy set
architecture:
  style: modular_monolith

service_boundaries:
  max_functions_per_service: 50
  group_by: domain

database:
  ownership: per_service
  shared_tables_allowed: false

deployment:
  runtime: containers
  orchestrator: kubernetes

Once this exists:

Architecture synthesis becomes deterministic.

Mitigation 1 — Define architecture style early

This is the first decision.

Not the last.

The three realistic options
Option A — Modular Monolith

Best for:

most legacy migrations
small teams
predictable scaling
Option B — Microservices

Best for:

large systems
high scaling needs
independent teams
Option C — Strangler pattern

Best for:

incremental migration.

For your case (1000 ColdFusion files):

Most likely optimal:

Modular monolith first.

Then evolve.

Mitigation 2 — Use domain-driven grouping

Instead of:

grouping by file structure

Group by:

business domain.

Example

Instead of:

user.cfc
user_utils.cfc
user_helper.cfc

Group into:

User Management Service

This prevents:

fragmented services.

Mitigation 3 — Use deterministic service boundary rules

You need rules like:

Rule examples
One service owns one primary database table

Functions that write the same table belong to the same service

Functions sharing session state belong to the same service

Maximum service size: 50 functions

These rules make architecture reproducible.

Mitigation 4 — Separate architecture design from code generation

Never combine them.

Wrong model
Generate service → generate code
Correct model
Design service → review → lock → generate code

You already hinted at this in your design — this is the right direction.

Mitigation 5 — Introduce architecture templates

Do not design from scratch every time.

Example template
service:
  type: REST

  layers:
    - controller
    - service
    - repository

  database:
    type: PostgreSQL

  communication:
    protocol: HTTP

Templates reduce decision load dramatically.

Mitigation 6 — Introduce architecture scoring

This prevents bad designs.

Metrics to score
coupling
cohesion
service size
dependency cycles
data ownership conflicts
Example
{
  "service": "UserService",
  "coupling": 0.32,
  "cohesion": 0.81,
  "cycles": 0,
  "score": "GOOD"
}

This turns architecture into:

measurable output.

Mitigation 7 — Make architecture incremental

Do not design the entire system at once.

Instead

Design:

one domain at a time.

Example order:

Authentication
Users
Orders
Payments
Reporting

This reduces risk dramatically.

Mitigation 8 — Visualize service boundaries

This is where your earlier graph discussion becomes very powerful again.

Instead of:

guessing service boundaries

You compute them.

Example dependency graph:

Functions
   ↓
Shared tables
   ↓
Clusters
   ↓
Services

This is deterministic clustering.

The architecture synthesis pipeline
Semantic Model
   ↓
Dependency Graph
   ↓
Domain Clustering
   ↓
Architecture Policies
   ↓
Service Design
   ↓
Review
   ↓
Lock
The single most powerful technique
Table Ownership Rule

This one rule prevents most architectural chaos.

Rule
A service owns the tables it writes.

Example:

UserService writes users table

Therefore:

UserService owns users table

Everything else follows.

How this applies directly to your 1000 ColdFusion files

Here is the realistic workflow.

Step 1 — Extract table usage

For every function:

Identify:

tables read
tables written
Step 2 — Build dependency graph

Nodes:

functions
tables

Edges:

reads
writes
Step 3 — Cluster by table ownership

This produces:

candidate services.

Step 4 — Apply architecture policies

This refines:

service boundaries.

Step 5 — Review architecture

Only once.

Not per file.

Step 6 — Lock architecture

Then generate code.

Where architecture synthesis usually fails

These are the three classic mistakes.

Mistake 1 — designing microservices too early

Start with:

modular monolith.

Mistake 2 — letting developers define services manually

Use rules.

Mistake 3 — mixing technical and business boundaries

Keep them separate.

Minimal architecture policy set for your system

You can start with this.

architecture:

  style: modular_monolith

service_rules:

  max_functions_per_service: 50

  group_by:
    - primary_table
    - domain

database:

  ownership:
    per_service

  shared_tables:
    allowed: false

communication:

  protocol: REST

This alone resolves most ambiguity.

The most important mindset shift

You are not designing architecture.

You are defining:

constraints that generate architecture.

If this were my system

I would implement these first.

Mandatory

Architecture policies
Service boundary rules
Table ownership rule
Architecture lock

Very high value

Dependency graph clustering
Architecture templates
Architecture scoring

Optional

AI-assisted design suggestions

5. Risk 5 — verification will become the credibility gate

Clients will trust the system based on:

verification reliability.

Not code generation.

You will likely need:

behavioral diffing
API contract testing
data migration validation
regression replay

This area will expand significantly.

**MITIGATION**

First — what Risk 5 really is

Verification risk = inability to prove the new system behaves the same as the old system.

Not:

unit tests failing
code bugs
performance issues

But:

lack of trustworthy evidence that behavior is preserved

The real failure mode

Most migrations validate:

code compiles
tests pass
deployment works

But production fails because:

business behavior changed silently

Example:

discount calculation differs by 1%
timezone logic shifts
validation rules loosen
authorization changes

These are not syntax errors.
They are behavioral drift.

Why this risk is especially critical in your scenario

With legacy ColdFusion:

You often do not have:

complete test coverage
formal API contracts
clear specifications

So verification must be:

derived from the running system

Not documentation.

The core insight

You do not verify code.

You verify:

behavioral equivalence

The five root causes of verification failures
1) Missing baseline behavior

You don’t know what “correct” means.

2) Incomplete test coverage

Typical legacy coverage:

unit tests: minimal
integration tests: partial
edge cases: undocumented
3) Data-dependent logic

Behavior depends on:

database state
configuration
user input
4) Side effects are invisible

Example:

emails sent
logs written
external APIs called
5) Verification happens too late

Most teams test only after migration.

That is too late.

The architectural mitigation principle

You don’t test after migration.

You:

observe behavior before migration.

The single most important mitigation
Build a Behavioral Baseline

Before changing anything.

What a baseline looks like
{
  "endpoint": "/users/123",
  "method": "GET",
  "status": 200,
  "response_hash": "a81c9f...",
  "db_reads": ["users"],
  "db_writes": [],
  "duration_ms": 42
}

This becomes:

your ground truth.

Mitigation 1 — Capture real traffic

This is the most powerful technique.

Method

Log:

request
response
status
headers
timing
Example
Request:
GET /orders/456

Response:
200
{
  "total": 89.50
}

Store:

hash(response)

Not full payload.

This creates:

replayable behavior.

Mitigation 2 — Build a replay engine

This is the heart of verification.

Flow
Captured Request
   ↓
Run against old system
   ↓
Run against new system
   ↓
Compare responses

Result:

MATCH
DIFFERENCE
Mitigation 3 — Introduce comparison tolerances

Perfect equality is unrealistic.

You need:

controlled tolerance.

Example
numeric_difference ≤ 0.01
timestamp_difference ≤ 1 second
order_of_fields ignored

Without tolerance:

false failures explode.

Mitigation 4 — Verify at multiple levels

Do not rely on one test type.

Level 1 — API response

Compare:

status code
response structure
key values
Level 2 — Database effects

Compare:

rows inserted
rows updated
rows deleted
Level 3 — Side effects

Compare:

emails triggered
events published
logs generated
Level 4 — Performance

Compare:

latency
throughput
Mitigation 5 — Use shadow testing

This is the safest production verification method.

Flow
User request
   ↓
Old system handles it
   ↓
Same request sent to new system
   ↓
Responses compared silently

Users never see the new system.

But you collect:

verification data.

Mitigation 6 — Introduce verification contracts

Every function must declare:

expected behavior.

Example
{
  "function": "createUser",
  "inputs": ["email", "password"],
  "outputs": ["userId"],
  "side_effects": ["insert users table"]
}

This defines:

what to verify.

Mitigation 7 — Build verification coverage metrics

You need visibility.

Example metrics
Endpoints verified: 87%
Database writes verified: 92%
Critical workflows verified: 100%

This becomes:

the migration readiness indicator.

Mitigation 8 — Use deterministic datasets

Random production data is unpredictable.

You need:

stable test data.

Example
Test user:
ID: 1001
Balance: 500.00

This ensures:

repeatable verification.

Mitigation 9 — Introduce regression snapshots

Capture system state before migration.

Example
users table:
row_count: 12,345
checksum: 8a7c9d...

After migration:

Compare.

This detects:

silent data corruption.

Mitigation 10 — Make verification incremental

Do not test the entire system every time.

Instead

Verify:

only affected components.

Example:

UserService changed
→ verify only user workflows
The verification architecture
Production System
   ↓
Traffic Capture
   ↓
Behavioral Baseline
   ↓
Replay Engine
   ↓
Comparison Engine
   ↓
Verification Report
Minimal verification stack for your system

You do not need enterprise tooling.

Start small.

Step 1 — Enable request logging

Mandatory.

Step 2 — Store request/response pairs

High value.

Step 3 — Build replay script

Very high value.

Step 4 — Compare outputs

Mandatory.

Step 5 — Track verification coverage

Critical.

Realistic scaling for your 1000-file system
Without mitigation

Verification becomes:

manual testing chaos.

With mitigation

Verification becomes:

automated evidence generation.

Typical distribution:

80% automated verification
15% exploratory testing
5% manual validation
Where verification usually fails

These are the three classic mistakes.

Mistake 1 — relying on unit tests alone

Unit tests do not capture system behavior.

Mistake 2 — testing only happy paths

Edge cases break production.

Mistake 3 — verifying only responses

Side effects matter just as much.

The most important design decision
Verification must run continuously during migration.

Not:

at the end.

If this were my system

I would implement these first.

Mandatory

Behavioral baseline
Replay engine
Response comparison
Coverage metrics

Very high value

Shadow testing
Database verification
Tolerance rules

Optional

Performance benchmarking
Chaos testing

The most important mindset shift

You are not proving the new system works.

You are proving:

the new system behaves the same.

6. Risk 6 — plugin / adapter ecosystem will determine success

Your architecture assumes:

source adapters
target adapters

That is correct.

But:

adapters will dominate engineering effort.

Not the core engine.

**MITIGATION**

First — what Risk 6 really is

Adapter risk = the number of integrations grows faster than the core system.

Not:

performance
AI quality
parsing accuracy

But:

maintenance explosion

The real failure mode

The core engine stays stable.

Adapters multiply.

You end up with:

Core Engine:     20k lines
Adapters:       120k lines
Maintenance:     dominated by adapters

This happens because every new system introduces:

a new source language
a new framework
a new database
a new API pattern
Why this risk is especially relevant to you

Your domain (app modernization) naturally involves:

obscure legacy languages
custom frameworks
inconsistent conventions

You already mentioned:

ColdFusion
COBOL
legacy stacks

That is exactly where adapter count explodes.

The core insight

You do not scale adapters by writing more adapters.

You scale adapters by:

standardizing the contract they implement.

The five root causes of adapter explosion
1) Adapters are too smart

They contain:

parsing logic
business logic
transformation logic

Instead of:

just translation logic.

2) No strict adapter interface

Every adapter evolves differently.

You get:

inconsistent behavior.

3) Tight coupling to the core engine

Adapters depend on:

internal implementation details.

So:

core changes break adapters.

4) Framework-specific assumptions

Example:

One adapter assumes:

Spring Boot.

Another assumes:

Express.js.

Now the system behaves differently.

5) No capability model

You don’t know what an adapter supports.

So the system guesses.

The architectural mitigation principle

You don’t manage adapters individually.

You manage:

capabilities.

The single most important mitigation
Introduce an Adapter Capability Contract

Every adapter must declare:

what it can do.

Not:

how it does it.

Example contract
{
  "adapter": "coldfusion",

  "capabilities": {
    "parse_ast": true,
    "extract_dependencies": true,
    "extract_data_flow": false,
    "generate_code": false
  },

  "language": "CFML",

  "version": "1.0"
}

Now the system can:

route behavior deterministically.

Mitigation 1 — Define a strict adapter interface

Adapters must implement:

a minimal, stable API.

Core interface
class Adapter:

    def parse(self, file):
        pass

    def extract_facts(self, ast):
        pass

    def generate(self, model):
        pass

    def verify(self, result):
        pass

This prevents:

adapter drift.

Mitigation 2 — Separate adapters into layers

Do not build monolithic adapters.

Split them.

Adapter layers
Language Adapter
Framework Adapter
Database Adapter
Runtime Adapter

Example:

Instead of:

ColdFusion Adapter

Use:

CFML Language Adapter
Adobe CF Runtime Adapter
MySQL Database Adapter

This dramatically reduces duplication.

Mitigation 3 — Introduce adapter composition

Adapters should be assembled, not written.

Example
ColdFusion + MySQL + REST

becomes:

CFML Adapter
+
SQL Adapter
+
HTTP Adapter

This turns:

N adapters

into:

combinations of components.

Mitigation 4 — Make adapters data-driven

Avoid hardcoding behavior.

Use:

configuration.

Example

Instead of:

if language == "cfml":

Use:

language:
  name: cfml
  file_extensions:
    - .cfm
    - .cfc

Now behavior changes without code changes.

Mitigation 5 — Introduce adapter versioning

Adapters evolve.

You must track compatibility.

Example
{
  "adapter": "cfml",
  "version": "2.1",
  "compatible_with_engine": ">=1.5"
}

This prevents:

silent breakage.

Mitigation 6 — Build an adapter test harness

Every adapter must pass:

the same tests.

Required tests
parse correctness
dependency extraction
error handling
performance

This ensures:

consistent quality.

Mitigation 7 — Introduce fallback adapters

Not all languages need full support.

Example

If parsing fails:

Use:

generic text adapter.

This prevents:

pipeline failure.

Mitigation 8 — Track adapter usage metrics

You need visibility.

Example metrics
Files processed by adapter: 842
Errors: 12
Coverage: 96%
Performance: 120 ms/file

This helps identify:

weak adapters.

Mitigation 9 — Introduce adapter lifecycle management

Adapters should have:

clear states.

Lifecycle
EXPERIMENTAL
SUPPORTED
DEPRECATED
RETIRED

This prevents:

uncontrolled growth.

Mitigation 10 — Build an adapter registry

Central catalog.

Example
Adapters:

CFML Parser
SQL Extractor
HTTP Generator
Go Code Generator

This becomes:

the system’s plugin directory.

The adapter architecture
Core Engine
   ↓
Adapter Interface
   ↓
Capability Registry
   ↓
Adapter Components
   ↓
Pipeline
Minimal adapter model for your system

You do not need dozens of adapters.

Start small.

Required adapters
1) Language adapter

ColdFusion parser.

2) Database adapter

SQL detection.

3) Web adapter

HTTP endpoint extraction.

4) Code generation adapter

Target language generator.

That’s it.

The biggest scaling strategy
Build fewer, more general adapters.

Instead of:

ColdFusion 2016 adapter
ColdFusion 2018 adapter
ColdFusion 2021 adapter

Build:

CFML adapter

Use configuration to handle differences.

Realistic scaling for your system
Without mitigation

Adapter count grows linearly with projects.

With mitigation

Adapter count grows logarithmically.

Example:

Projects: 10
Adapters without control: 30
Adapters with control: 8
Where adapter systems usually fail

These are the three classic mistakes.

Mistake 1 — embedding business logic in adapters

Adapters should translate, not decide.

Mistake 2 — building project-specific adapters

Always build reusable adapters.

Mistake 3 — skipping adapter contracts

This leads to chaos quickly.

The most important design decision
Treat adapters as infrastructure — not features.

They must be:

stable
minimal
reusable

If this were my system

I would implement these first.

Mandatory

Strict adapter interface
Capability contract
Adapter composition
Test harness

Very high value

Adapter registry
Versioning
Metrics

Optional

Dynamic plugin loading
Marketplace-style adapter distribution

The most important mindset shift

You are not building:

many adapters.

You are building:

a platform that controls adapters.

Risk 7 — orchestration state management will get complex

You already have:

checkpoints
locks
corrections
artifacts

Soon you will need:

workflow state engine

Not just CLI flow.
**MITIGATION**

First — what Risk 7 really is

Orchestration state risk = losing track of what has happened, what is in progress, and what is safe to run next.

Not:

scheduling
performance
concurrency

But:

state correctness over time

The real failure mode

The pipeline runs fine until:

process crashes
network fails
review delayed
file changes mid-run

Then the system cannot answer:

What is complete?
What needs retry?
What is safe to regenerate?
What is locked?

That’s the risk.

Why this risk is especially relevant to your scenario

You already have (or plan to have):

checkpoints
locks
incremental runs
review gates
retries
long-running workflows

That combination requires:

durable workflow state

Without it, you get:

duplicated work
inconsistent outputs
broken locks
manual recovery
The core insight

You are not building:

a pipeline.

You are building:

a state machine.

The five root causes of orchestration state problems
1) Implicit state

State exists only in:

logs
filenames
memory

Instead of:

a structured store.

2) Non-idempotent steps

Running a step twice produces different results.

Example:

generate code → overwrite existing file
3) No recovery model

After failure:

the only option is:

restart everything.

4) State scattered across components

Example:

CLI tracks progress
database tracks locks
filesystem tracks outputs

No single source of truth.

5) Long-running workflows

Modernization pipelines often run:

hours or days.

That makes crashes inevitable.

The architectural mitigation principle

You don’t orchestrate steps.

You orchestrate:

state transitions.

The single most important mitigation
Introduce an explicit Workflow State Machine

Every artifact must have:

a lifecycle.

Example lifecycle
DISCOVERED
PARSED
FACTS_EXTRACTED
SEMANTICS_REVIEWED
SEMANTICS_LOCKED
ARCHITECTURE_ASSIGNED
CODE_GENERATED
VERIFIED
DEPLOYED
FAILED

Now the system always knows:

where each artifact is
Mitigation 1 — Make every step idempotent

This is the most critical reliability property.

Definition

Running the same step twice produces the same result.

Example

Bad:

generate_service()

Good:

generate_service_if_missing()
Rule

Every step must be:

safe to retry.

Mitigation 2 — Use durable state storage

Never store workflow state only in memory.

Minimum viable store

SQLite.

Not logs.

Not files.

Example schema
artifacts
---------
id
type
state
version
checksum
updated_at

This becomes:

the system’s memory.

Mitigation 3 — Introduce checkpoints

Save progress after every stage.

Example
parse completed
→ checkpoint saved

facts extracted
→ checkpoint saved

After failure:

resume from:

last checkpoint.

Mitigation 4 — Separate orchestration from execution

Execution does work.

Orchestration manages state.

Instead of
CLI runs everything
Use
Orchestrator
   ↓
Workers

Workers are:

stateless.

Mitigation 5 — Introduce retry policies

Failures are normal.

Retries must be automatic.

Example
retry_count: 3
backoff: exponential
timeout: 60 seconds

Without retries:

pipelines become fragile.

Mitigation 6 — Track step history

You need an audit trail.

Example
Artifact: userService

History:

PARSED
FACTS_EXTRACTED
FAILED
RETRIED
FACTS_EXTRACTED
SEMANTICS_LOCKED

This enables:

debugging and trust.

Mitigation 7 — Use optimistic locking

Prevent concurrent corruption.

Example
update artifact
only if version matches

This avoids:

race conditions.

Mitigation 8 — Introduce failure states

Do not hide failures.

Required states
FAILED
RETRYING
BLOCKED
CANCELLED

This makes failures visible and manageable.

Mitigation 9 — Build resumable workflows

This is essential for large systems.

Instead of
restart pipeline
Use
resume from last state

Example:

1000 files

900 completed
100 pending

resume only remaining
Mitigation 10 — Add observability

You need visibility into system state.

Key metrics
artifacts in progress
artifacts completed
artifacts failed
average processing time
retry count

Without observability:

orchestration becomes guesswork.

The orchestration architecture
CLI / API
   ↓
Orchestrator
   ↓
State Store
   ↓
Workers
   ↓
Artifacts

The orchestrator:

does not do work.

It:

moves state forward.

Minimal implementation for your system

You do not need a distributed system.

Start simple.

Step 1 — Define artifact states

Mandatory.

Step 2 — Store state in SQLite

Very high value.

Step 3 — Make steps idempotent

Critical.

Step 4 — Add checkpoints

Mandatory.

Step 5 — Add retry logic

High value.

Realistic scaling for your 1000-file system
Without mitigation

You get:

inconsistent outputs
manual restarts
lost progress
debugging chaos
With mitigation

You get:

predictable recovery
incremental progress
safe retries
clear visibility
Where orchestration systems usually fail

These are the three classic mistakes.

Mistake 1 — treating orchestration as scripting

Example:

run step1
run step2
run step3

This breaks at scale.

Mistake 2 — storing state in logs

Logs are not state.

Mistake 3 — ignoring partial completion

Large workflows always complete partially.

Design for it.

The most important design decision
Every artifact must always be in exactly one state.

No ambiguity.

No hidden progress.

If this were my system

I would implement these first.

Mandatory

Explicit state machine
Durable state store
Idempotent steps
Checkpoints

Very high value

Retry policies
Audit history
Resumable workflows

Optional

Distributed workers
Parallel orchestration

The most important mindset shift

You are not managing tasks.

You are managing:

state transitions over time.