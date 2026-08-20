# Implementation Plan for Codex

Build sequentially. Each phase should leave the repo runnable and tested.

## Phase 0 — Repository foundation
Deliver:
- monorepo directories
- Next.js web app
- FastAPI API
- Postgres + Redis + worker in Docker Compose
- migrations
- Makefile
- `.env.example`
- CI skeleton
- local auth/workspace bootstrap
- health endpoints

Acceptance:
- `docker compose up` starts stack
- web loads
- API health passes
- DB migration passes
- `make lint`, `make typecheck`, basic tests pass

## Phase 1 — Canonical schemas and storage
Deliver Pydantic/domain schemas and DB models for:
- agent/config versions
- conversation/turns
- retrieval/chunks
- tools/tool calls
- KB sources
- datasets
- eval definitions/suites/runs/results
- findings/recommendations/reviews

REST CRUD/read endpoints as needed.

Acceptance:
- round-trip canonical trace fixture
- schema validation tests
- workspace isolation tests
- migration tests

## Phase 2 — Ingestion
Deliver:
- JSON/JSONL import
- CSV transcript mapping
- REST single/batch ingestion
- generic webhook event ingestion
- idempotency
- import preview/errors
- Integration Maturity calculation

Acceptance:
- demo traces import successfully
- malformed records reported without corrupting valid records
- duplicate ingestion idempotent
- webhook out-of-order fixture reconstructs trace

## Phase 3 — LLM Gateway and provider adapters
Deliver:
- gateway interface
- provider registry
- OpenAI adapter
- Anthropic adapter
- Gemini adapter
- OpenAI-compatible adapter
- Ollama adapter
- structured output validation
- normalized usage/errors
- provider connection UI
- environment and encrypted-DB secret modes

Acceptance:
- mocked contract tests for all providers
- at least one live-provider smoke test when credential exists, skipped otherwise
- key never returned through API/UI
- provider switch requires no evaluator code changes

## Phase 4 — Eval engine foundation
Deliver:
- declarative eval definitions
- eval suite runner
- async jobs
- response/rubric evaluator
- conversation-quality evaluator
- result provenance
- run status/progress
- basic run UI

Acceptance:
- demo rubric failures detected
- multilingual fixture evaluated with same schema
- partial evaluator failure does not corrupt run

## Phase 5 — Grounding + RAG
Deliver:
- claim extraction/grounding evaluator
- evidence resolution
- knowledge availability evaluator
- retrieval recall/ranking/precision/conflict/utilization evaluator
- grounding/RAG dashboards

Acceptance:
- seeded unsupported and contradicted claims classified correctly
- seeded knowledge gap vs retrieval miss distinguished
- source/chunk evidence links work

## Phase 6 — Tool trajectory
Deliver:
- selection/timing/arguments/provenance/result-use evaluator
- tool analytics/funnel/detail UI

Acceptance:
- seeded early call, missing arg, wrong arg, and contradicted result detected
- unavailable tool is not incorrectly penalized

## Phase 7 — Findings + root cause
Deliver:
- finding clustering
- root cause synthesizer
- failure ownership analytics
- Finding list/detail UI
- language distribution and trends

Acceptance:
- repeated failures cluster into one Finding
- retrieval miss with hallucination attributes retrieval as primary cause
- evidence references remain navigable

## Phase 8 — Recommendations + human review
Deliver:
- recommendation engine
- prompt diff rendering
- KB-gap safe recommendations
- tool definition/policy patch suggestions
- review state machine
- audit log
- copy/export patch

Acceptance:
- no automatic production change path exists
- approving recommendation creates approved/exportable draft artifact only
- unknown KB facts are not fabricated

## Phase 9 — Regression evaluation
Deliver:
- candidate prompt patch representation
- baseline vs candidate run
- fixed/new-regression comparison
- Recommendation review validation panel
- add confirmed production failure to dataset

Acceptance:
- demo candidate fixes seeded issue
- new seeded regression is surfaced
- critical regression prevents “safe” recommendation status

## Phase 10 — Analytics and multilingual parity
Deliver polished Overview:
- quality/risk
- KPI strip
- trends
- needs attention
- failure ownership
- language performance
- eval coverage
- provider/cost health

Acceptance:
- filters propagate consistently
- low-volume language warning works
- code-switched conversations represented correctly

## Phase 11 — CLI, SDK, docs, demo
Deliver:
- Python SDK
- CLI
- README quickstart
- API docs/examples
- contributor docs
- multilingual demo dataset
- `make demo`

Acceptance:
Fresh clone path works from documented commands.

## Phase 12 — Final hardening
- security tests
- accessibility smoke tests
- performance sanity for batch ingestion/eval queue
- CI full suite
- clean failure states
- final E2E suite
- `FINAL_VERIFICATION.md`

## Suggested GitHub Actions
Jobs:
- backend lint/type/unit
- frontend lint/type/unit
- integration with Postgres/Redis services
- Playwright E2E against Docker/CI stack
- schema/migration check
- secret scan/dependency scan where practical

## Codex progress artifact
Create/update `BUILD_STATUS.md` after each phase:
- Done
- Tests run/results
- Decisions/ADRs
- Known limitations
- Next phase
