# Modernization Demo App

This directory contains a Python-based modernization demo tool that takes a small ColdFusion source set through a staged pipeline and produces a runnable Python + React target application.

The demo is intentionally artifact-driven. Each stage writes inspectable outputs into `.modernize/`, and later stages are gated by review and lock artifacts rather than by implicit in-memory state.

## What This Demo Covers

- source and config discovery
- deterministic AST-like parsing
- deterministic fact extraction
- pluggable AI-assisted semantic derivation
- semantic review, correction, and lock
- source architecture derivation, review, and lock
- target architecture derivation, review, and lock
- generation of a runnable Python backend + React frontend
- lightweight verification
- audit logging and stale-lock detection

## Prerequisites

- Python `3.11+`
- `jinja2`
- `tree-sitter`
- `tree-sitter-language-pack`
- Node.js is optional
  Node is not required to run the generated frontend because the demo serves a CDN-based React app, but it is useful if you want to inspect frontend assets manually.

The current implementation uses:

- Python standard library for the CLI, backend runtime, tests, and HTTP serving
- `jinja2` for deterministic Markdown document rendering
- `tree-sitter` plus `tree-sitter-language-pack` for source parsing

## AI Provider Model

The semantic stage is provider-driven rather than bound to one model vendor.

Supported provider modes:

- `demo-ai`
  Offline fallback used for local development and tests.
- `openai`
  Native OpenAI SDK adapter.
- `anthropic`
  Native Anthropic SDK adapter.
- `gemini`
  Native Google Gemini SDK adapter.
- `command-json`
  Runs any local command that reads JSON from `stdin` and writes JSON to `stdout`.
- `python:<module>:<symbol>`
  Loads a Python provider class or factory directly.

This means the tool can leverage whatever AI is available to you:

- OpenAI, Anthropic, or Gemini via native adapters
- a local open-source model served by a script or CLI
- a custom in-repo Python adapter

The core app does not assume one vendor. It assumes a provider contract.

### Common Provider Interface

All AI providers implement the same conceptual interface defined in:

- [base.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/base.py)

The provider must expose:

- a `name`
- a `derive_semantics(facts)` method
- a `generate_application(generation_context)` method

That method must return a normalized semantic derivation with:

- `summary`
- `module_role`
- `business_capabilities`
- `confidence`
- `field_confidences`
- `provider`

The generation method must return:

- `files`
- `provider`
- `notes`

The registry that resolves provider strings lives in:

- [registry.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/registry.py)

### Native Provider Environment Variables

- `openai`
  - `OPENAI_API_KEY`
  - optional `MODERNIZE_OPENAI_MODEL`
- `anthropic`
  - `ANTHROPIC_API_KEY`
  - optional `MODERNIZE_ANTHROPIC_MODEL`
- `gemini`
  - `GEMINI_API_KEY`
  - or `GOOGLE_API_KEY`
  - or Google Application Default Credentials for Vertex AI
  - `GOOGLE_CLOUD_PROJECT` required for ADC / Vertex AI mode
  - optional `MODERNIZE_GEMINI_MODEL`
  - optional `GOOGLE_CLOUD_LOCATION`
  - optional `GOOGLE_GENAI_USE_VERTEXAI=true`

Example shell setup:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

Or copy the checked-in environment template and source it before running the CLI:

```bash
cp .env.example .env
# edit .env and uncomment the provider settings you want
source .env
```

The template lives at:

- [.env.example](/Users/koustubh/Documents/modern-app/app/.env.example)

### Gemini With Google Application Default Credentials

If getting a Gemini API key is inconvenient, the Gemini provider can also use Google Application Default Credentials through Vertex AI.
This includes personal user credentials created with `gcloud auth application-default login`, not just service-account JSON keys.

Typical setup:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI=true
python3 modernize.py choose-provider --provider gemini
```

You can also use a service-account JSON file instead of personal ADC:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI=true
python3 modernize.py choose-provider --provider gemini
```

In other words, the Gemini adapter now supports both:

- API key auth via `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- Google Cloud ADC / Vertex AI auth via personal credentials from `gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS`

### `command-json` Provider Contract

If you initialize with:

```bash
python3 modernize.py init ../mock_tool/sample_app --provider command-json
```

then set:

```bash
export MODERNIZE_AI_COMMAND="python3 /absolute/path/to/your/provider_script.py"
```

The command receives JSON on `stdin`:

```json
{
  "task": "derive_semantics",
  "facts": { "...": "fact artifact for one module" },
  "outputSchema": {
    "summary": "string",
    "moduleRole": "string",
    "businessCapabilities": [
      {
        "function": "string",
        "description": "string",
        "confidence": "0..100 int"
      }
    ],
    "confidence": "0..100 int",
    "fieldConfidences": {
      "summary": "0..100 int",
      "moduleRole": "0..100 int",
      "businessCapabilities": "0..100 int"
    }
  }
}
```

And it must return JSON on `stdout`:

```json
{
  "summary": "Login handles sign-in and delegates identity checks.",
  "moduleRole": "request-entrypoint",
  "businessCapabilities": [
    {
      "function": "render_login",
      "description": "Handles login form orchestration.",
      "confidence": 88
    }
  ],
  "confidence": 87,
  "fieldConfidences": {
    "summary": 89,
    "moduleRole": 91,
    "businessCapabilities": 88
  }
}
```

## Contributing AI Providers

There are two supported ways to add a new provider.

### 1. Wrap An External AI With `command-json`

This is the easiest path if you already have:

- an Anthropic client script
- a Gemini wrapper
- an OpenAI wrapper
- a local model CLI
- any other executable that can read JSON and write JSON

You do not need to change the demo codebase for this path. Just:

1. write a wrapper script that reads the fact artifact payload from `stdin`
2. call your chosen AI system
3. return the normalized JSON response on `stdout`
4. run:

```bash
python3 modernize.py choose-provider --provider command-json
export MODERNIZE_AI_COMMAND="python3 /absolute/path/to/your/provider_script.py"
```

This is the best option when:

- you want to use whatever AI is available locally
- you do not want to add provider-specific code to this repo
- you want a stable integration contract

### 2. Add A Native Python Provider

This is the better path if you want a first-class in-repo adapter.

Add a provider under:

- [adapters/ai/](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai)

Typical structure:

1. create a new file such as:
   - `modernize_demo/adapters/ai/my_provider.py`
2. define a class with:
   - `name = "my-provider"`
   - `derive_semantics(self, facts) -> SemanticDerivation`
3. return a `SemanticDerivation` object from [base.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/base.py)
4. either:
   - load it dynamically with `python:<module>:<symbol>`, or
   - extend [registry.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/registry.py) with a friendly alias

Minimal shape:

```python
from modernize_demo.adapters.ai.base import SemanticDerivation


class MyProvider:
    name = "my-provider"

    def derive_semantics(self, facts: dict) -> SemanticDerivation:
        return SemanticDerivation(
            summary="...",
            module_role="...",
            business_capabilities=[
                {
                    "function": "render_login",
                    "description": "...",
                    "source": "ai",
                    "confidence": 88,
                }
            ],
            confidence=87,
            field_confidences={
                "summary": 89,
                "moduleRole": 91,
                "businessCapabilities": 88,
            },
            provider=self.name,
        )
```

Then select it with:

```bash
python3 modernize.py choose-provider --provider python:modernize_demo.adapters.ai.my_provider:MyProvider
```

### What A Good Provider Should Do

- consume one fact artifact at a time
- keep confidence on a `0..100` scale
- return structured JSON/data, not free-form prose
- make the provider name explicit
- fail loudly when the upstream AI call is malformed or incomplete

### Recommended Contribution Pattern

If you contribute a new in-repo provider, also add:

- unit tests for the provider itself
- one integration path showing it works with `extract`
- README notes for any required environment variables

The existing examples are:

- [demo_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/demo_provider.py)
- [openai_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/openai_provider.py)
- [anthropic_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/anthropic_provider.py)
- [gemini_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/gemini_provider.py)
- [command_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/command_provider.py)
- [test_ai_providers.py](/Users/koustubh/Documents/modern-app/app/tests/unit/test_ai_providers.py)

## Parsing Strategy

The ColdFusion source adapter is Tree-sitter-backed.

For this demo, CFML files are parsed through the Tree-sitter HTML grammar shipped by `tree-sitter-language-pack`. That gives the tool structured nodes for CFML tags such as:

- `cfcomponent`
- `cffunction`
- `cfargument`
- `cfquery`
- `cfif`
- `cfset`
- `cfthrow`
- `cfform`
- `cfinput`

This is still a demo-oriented parsing strategy because it is not a dedicated CFML grammar, but it is no longer regex-based parsing.

## Virtual Environment

A virtual environment has been created at:

- [app/.venv](/Users/koustubh/Documents/modern-app/app/.venv)

Activate it with:

```bash
cd /Users/koustubh/Documents/modern-app/app
source .venv/bin/activate
```

If you need to recreate it:

```bash
cd /Users/koustubh/Documents/modern-app/app
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
```

## Repo Layout

- CLI entrypoint: [modernize.py](/Users/koustubh/Documents/modern-app/app/modernize.py)
- Core package: [modernize_demo/](/Users/koustubh/Documents/modern-app/app/modernize_demo)
- Tests: [tests/](/Users/koustubh/Documents/modern-app/app/tests)

## Running The Demo

All commands below assume you are inside [app/](/Users/koustubh/Documents/modern-app/app).

```bash
cd /Users/koustubh/Documents/modern-app/app
source .venv/bin/activate
```

You can point the tool at any small ColdFusion directory. For local testing in this repo, a convenient source set already exists at:

- [mock_tool/sample_app](/Users/koustubh/Documents/modern-app/mock_tool/sample_app)

### 1. Initialize The Project

```bash
python3 modernize.py init ../mock_tool/sample_app
```

This creates `.modernize/` and writes initial migration state. The target stack is intentionally not chosen at this stage.

For a real AI-backed run, choose a provider during init, for example:

```bash
python3 modernize.py init ../mock_tool/sample_app --provider command-json
```

Built-in native providers are also available:

```bash
python3 modernize.py init ../mock_tool/sample_app --provider openai
python3 modernize.py init ../mock_tool/sample_app --provider anthropic
python3 modernize.py init ../mock_tool/sample_app --provider gemini
```

Or keep the default and switch providers interactively afterward:

```bash
python3 modernize.py choose-provider
```

If you stay on the default `demo-ai`, the `extract` stage will warn you that the offline fallback is still active. `init` itself does not prompt for provider selection.

### 2. Discover Source And Config Inputs

```bash
python3 modernize.py discover
```

This writes:

- `.modernize/discovery/source-discovery.json`
- `.modernize/discovery/demo-slice.json`

### 3. Parse Source To AST Artifacts

```bash
python3 modernize.py parse
```

This writes one AST artifact per module under:

- `.modernize/ast/`

### 4. Extract Deterministic Facts

```bash
python3 modernize.py facts
```

This writes one fact artifact per module under:

- `.modernize/facts/`

### 5. Derive Semantics

```bash
python3 modernize.py extract
```

This writes:

- semantic artifacts under `.modernize/semantics/`
- semantic review state at `.modernize/semantics/review-state.json`

### 6. Review Semantics

Inspect all semantic review state:

```bash
python3 modernize.py review semantics
```

Inspect a single module:

```bash
python3 modernize.py review semantics login
```

Apply a correction:

```bash
python3 modernize.py correct semantics login --field summary --value "Login handles sign-in and delegates identity checks."
```

Approve all semantic artifacts:

```bash
python3 modernize.py approve semantics --all
```

### 7. Lock Semantics

```bash
python3 modernize.py lock semantics
```

This writes:

- `.modernize/locked/semantic-lock.json`
- `.modernize/locked/lock-manifest.json`

### 8. Derive Source Architecture

```bash
python3 modernize.py source-architect
```

This writes:

- `.modernize/architecture/source-architecture.json`
- `.modernize/architecture/source-architecture.md`
- `.modernize/architecture/source-architecture-review.json`

### 9. Review And Lock Source Architecture

Review:

```bash
python3 modernize.py review source-architecture
```

Approve:

```bash
python3 modernize.py approve source-architecture
```

Lock:

```bash
python3 modernize.py lock source-architecture
```

This writes:

- `.modernize/locked/source-architecture-lock.json`

### 10. Choose The Target Stack

Pick the target stack only after source architecture has been reviewed and locked. This step now also captures the intended architectural style and deployment style:

```bash
python3 modernize.py choose-target-stack \
  --target-stack python:backend,react:frontend \
  --architecture-style service-oriented \
  --deployment-style single-deployable
```

This writes:

- `.modernize/architecture/target-stack.json`

### 11. Derive Target Architecture

```bash
python3 modernize.py target-architect
```

This writes:

- `.modernize/architecture/target-architecture.json`
- `.modernize/architecture/target-architecture.md`
- `.modernize/architecture/target-adapter-conventions.json`
- `.modernize/architecture/target-architecture-review.json`

### 12. Review And Lock Target Architecture

Review:

```bash
python3 modernize.py review target-architecture
```

Approve:

```bash
python3 modernize.py approve target-architecture
```

Lock:

```bash
python3 modernize.py lock target-architecture
```

This writes:

- `.modernize/locked/target-architecture-lock.json`

### 13. Generate The Runnable Target App

```bash
python3 modernize.py generate demo-app
```

This writes the generated application under:

- `.modernize/services/demo-app/`

`generate` now builds a rich locked context from:

- AST artifacts
- fact artifacts
- reviewed semantic artifacts
- locked source architecture
- locked target architecture
- target adapter conventions

and passes that context to the selected AI provider for backend/frontend code synthesis. The `demo-ai` provider keeps a deterministic fallback path for tests and offline demos.

Important generated files:

- `.modernize/services/demo-app/backend/server.py`
- `.modernize/services/demo-app/backend/app_logic.py`
- `.modernize/services/demo-app/frontend/index.html`
- `.modernize/services/demo-app/frontend/app.js`

### 14. Verify Generated Behavior

```bash
python3 modernize.py verify demo-app
```

This writes:

- `.modernize/recordings/demo-app/verification-report.json`

### 15. Check Project Status

```bash
python3 modernize.py status
```

This reports:

- pipeline step status
- lock existence
- semantic-lock stale status

## Full Happy-Path Command Order

```bash
python3 modernize.py init ../mock_tool/sample_app
python3 modernize.py choose-provider
python3 modernize.py discover
python3 modernize.py parse
python3 modernize.py facts
python3 modernize.py extract
python3 modernize.py review semantics
python3 modernize.py correct semantics login --field summary --value "Login handles sign-in and delegates identity checks."
python3 modernize.py approve semantics --all
python3 modernize.py lock semantics
python3 modernize.py source-architect
python3 modernize.py review source-architecture
python3 modernize.py approve source-architecture
python3 modernize.py lock source-architecture
python3 modernize.py choose-target-stack --target-stack python:backend,react:frontend --architecture-style service-oriented --deployment-style single-deployable
python3 modernize.py target-architect
python3 modernize.py review target-architecture
python3 modernize.py approve target-architecture
python3 modernize.py lock target-architecture
python3 modernize.py generate demo-app
python3 modernize.py verify demo-app
python3 modernize.py status
```

## Running The Happy Path With `doitlive`

The app includes a ready-made `doitlive` session file for the full happy path:

- [doitlive/happy-path.sh](/Users/koustubh/Documents/modern-app/app/doitlive/happy-path.sh)

From [app/](/Users/koustubh/Documents/modern-app/app):

```bash
source .venv/bin/activate
pip install -r requirements.txt
doitlive play doitlive/happy-path.sh --shell /bin/zsh
```

Useful options from the official docs:

- `doitlive play doitlive/happy-path.sh -p sorin`
- `doitlive play doitlive/happy-path.sh -s 3`
- `doitlive themes --preview`

The session file uses comment echo, so your stage notes appear inline while you advance through the commands.

## Running The Generated App

From [app/](/Users/koustubh/Documents/modern-app/app):

```bash
source .venv/bin/activate
python3 .modernize/services/demo-app/backend/server.py
```

Then open:

- `http://127.0.0.1:8787/`

Useful endpoints:

- `GET /health`
- `POST /api/login`
- `GET /api/users?user_id=1`
- `GET /api/orders?user_id=1`
- `POST /api/orders`

You can change the port with:

```bash
source .venv/bin/activate
MODERNIZE_DEMO_PORT=9000 python3 .modernize/services/demo-app/backend/server.py
```

## Running Tests

Run the full suite:

```bash
PYTHONPATH=/Users/koustubh/Documents/modern-app/app ./.venv/bin/python -m unittest discover -s tests
```

Run phase-specific suites:

```bash
PYTHONPATH=/Users/koustubh/Documents/modern-app/app ./.venv/bin/python -m unittest discover -s tests/unit -p 'test_phase1_foundation.py'
PYTHONPATH=/Users/koustubh/Documents/modern-app/app ./.venv/bin/python -m unittest discover -s tests/integration -p 'test_phase2_3_pipeline.py'
PYTHONPATH=/Users/koustubh/Documents/modern-app/app ./.venv/bin/python -m unittest discover -s tests/integration -p 'test_phase4_6_architecture.py'
PYTHONPATH=/Users/koustubh/Documents/modern-app/app ./.venv/bin/python -m unittest discover -s tests/integration -p 'test_phase7_8_generation.py'
```

## Notes

- The CLI prints JSON payloads for every command so stages are easy to inspect and easy to test.
- Locks are real gating artifacts. If discovery changes after a lock is created, `status` will report stale lock state.
- The generated frontend uses CDN-hosted React rather than a local build pipeline. That keeps the demo lightweight while still producing a real browser UI.
- `extract` and `generate` are both provider-driven. `extract` uses AI for semantic derivation. `generate` uses AI for backend/frontend code synthesis from locked artifacts.
- For production-style runs, prefer `--provider command-json` or `--provider python:<module>:<symbol>` instead of the offline `demo-ai` fallback.
- Built-in native provider code lives under [adapters/ai/](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai) and includes OpenAI, Anthropic, and Gemini adapters.
- AI provider adapter code lives under [adapters/ai/](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai):
  - [registry.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/registry.py)
  - [openai_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/openai_provider.py)
  - [anthropic_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/anthropic_provider.py)
  - [gemini_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/gemini_provider.py)
  - [command_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/command_provider.py)
  - [demo_provider.py](/Users/koustubh/Documents/modern-app/app/modernize_demo/adapters/ai/demo_provider.py)

## Demo Presenter Flow

If you are using this in front of engineers and directors, this is the cleanest walkthrough order:

1. Show the source input directory.
2. Run `discover`, `parse`, and `facts` to show deterministic artifact creation.
3. Run `choose-provider`, then `extract` and `review semantics` to show the AI-assisted layer.
4. Apply one correction with `correct semantics ...` to demonstrate human intervention.
5. Approve and lock semantics.
6. Generate and show the source architecture document.
7. Choose the target stack, then generate, review, and lock the target architecture.
8. Generate `demo-app`.
9. Start the generated backend and open the generated frontend in a browser.
10. Run `verify demo-app`.
11. Change one source file, rerun `discover`, then show `status` so the stale lock behavior is visible.

That sequence usually tells the right story:

- deterministic understanding first
- controlled AI assistance second
- governance through review and locks
- architecture as an approved intermediate artifact
- working generated output at the end
