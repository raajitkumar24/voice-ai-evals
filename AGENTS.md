# AGENTS.md — Voice AI Evals

## Mission
Build and maintain an open-source, self-hostable, multilingual, LLM-provider-agnostic evaluation and observability platform for Voice AI agents.

The product must ingest real agent traces, evaluate response quality, grounding/hallucination, RAG quality, tool use, and conversation behavior, synthesize root causes, and generate human-reviewable recommendations. It must never autonomously modify production agent prompts, knowledge bases, tool definitions, or external agent configuration.

## Non-negotiable product principles
1. **Human approval is mandatory.** Recommendations are suggestions only. No automatic mutation of production configuration.
2. **Provider agnostic.** Core eval logic must not import vendor SDKs directly. All model calls go through the LLM Gateway/provider adapters.
3. **Voice-platform agnostic.** Core eval logic depends only on canonical schemas, never provider-specific conversation formats.
4. **Multilingual by default.** Evaluation semantics must be the same across languages. Original text is the source of truth; translations are optional reviewer aids.
5. **Traceability.** Every eval result must record evaluator version, rubric version, model/provider, input trace IDs, timestamps, and confidence.
6. **Evidence before recommendation.** Findings and recommendations must be linked to observable call/turn/tool/retrieval evidence.
7. **Immutable source traces.** Raw ingested traces are append-only/immutable. Derived evals/findings may be recomputed.
8. **No hidden self-healing.** Provider fallback, retries, and judge consensus must be visible in run metadata.
9. **Cost-aware.** Track token usage, model/provider usage, latency, and estimated cost where pricing data is available.
10. **Safe secrets.** Never store provider API keys in browser storage, logs, telemetry, error traces, or source control.

## Required stack
Use the following unless a documented blocker is discovered:
- Web: Next.js + TypeScript + Tailwind + shadcn/ui + Recharts
- API: Python + FastAPI + Pydantic + SQLAlchemy
- Database: PostgreSQL
- Async jobs: Redis + Celery (or Dramatiq only if there is a strong implementation reason, documented in ADR)
- Tests: pytest, Playwright, Vitest/Jest where appropriate
- Containers: Docker + Docker Compose
- API schema: OpenAPI generated from FastAPI

## Repository architecture
Maintain clean boundaries:
- `apps/web`: UI only; no provider SDK logic.
- `apps/api`: HTTP API, auth, orchestration endpoints.
- `workers/eval-worker`: async eval execution.
- `packages/eval-core`: evaluator orchestration and domain logic.
- `packages/schemas`: canonical Pydantic/domain schemas.
- `packages/llm-gateway`: vendor-neutral model interface, routing, retries, structured output validation.
- `packages/llm-providers`: provider adapters only.
- `packages/connectors`: voice-agent/data-source adapters only.
- `packages/sdk`: public client SDK(s).
- `evals`: declarative evaluator definitions/prompts/versioned schemas.
- `tests`: unit/integration/e2e fixtures and test suites.

No circular imports across these boundaries.

## Canonical dependency rule
Provider-specific objects must be normalized before entering `eval-core`.

Forbidden:
`eval-core -> openai SDK / anthropic SDK / google SDK / vapi SDK / retell SDK`

Allowed:
`eval-core -> llm-gateway -> provider adapter`
`connector -> canonical ConversationTrace -> eval-core`

## LLM provider contract
All LLM adapters must implement a common interface with at least:
- test_connection
- list_models (if provider supports it)
- generate
- generate_structured
- usage normalization
- error normalization
- capability declaration

The product must initially support:
- OpenAI
- Anthropic
- Google Gemini
- OpenAI-compatible endpoint
- Ollama/local endpoint

Architect for later Azure OpenAI and AWS Bedrock support.

Never hard-code a model name as a permanent default. Models must be configurable and capability-validated.

## Multilingual rules
- Store original utterance text unchanged.
- Store detected language per turn when available.
- Support code-switching metadata.
- Do not require translation to evaluate a call.
- Optional translations must be clearly labeled and never overwrite originals.
- Language is a filter/analytic dimension, not a separate eval pipeline.
- Test fixtures must include English, Hindi, Hinglish, Tamil, and Malayalam.

## Human review workflow
Recommendation state machine:
`GENERATED -> PENDING_REVIEW -> APPROVED | REJECTED | EDITED`

If approved, the product may create/export a **draft patch artifact** only. It must not modify an external production agent automatically.

For V1, all external agent integrations are read-only. Recommended actions are copy/export/download only.

## Evaluation families
Implement separately:
1. Rubric/response quality
2. Grounding and hallucination
3. RAG/knowledge/retrieval
4. Tool trajectory
5. Conversation behavior
6. Root-cause synthesis
7. Recommendation generation

Do not implement one giant “evaluate this call” prompt.

## Eval output contract
Every evaluator output must be structured, schema-validated, and include:
- verdict: PASS | FAIL | NOT_APPLICABLE | UNCERTAIN
- confidence: 0..1
- severity
- reason
- evidence references
- evaluator id/version
- provider/model provenance
- failure taxonomy code when applicable

Never build analytics by parsing free-form judge prose.

## Development workflow
Before coding a feature:
1. Read relevant specs in `/docs`.
2. Identify affected canonical schemas and API contracts.
3. Add/update tests first or in the same commit.
4. Implement smallest complete vertical slice.
5. Run affected unit/integration tests.
6. Run lint/typecheck.
7. For user-visible workflows, run Playwright E2E.
8. Update docs/examples if public behavior changed.

## Definition of done
A task is not done until:
- implementation is complete;
- tests cover happy path + meaningful failure modes;
- types/lint pass;
- migrations exist for DB changes;
- no secrets or credentials are committed;
- user-visible errors are understandable;
- API behavior is documented;
- relevant E2E flow passes;
- existing regression suite passes.

## Testing commands
Codex should create and keep these commands working:
- `make setup`
- `make dev`
- `make lint`
- `make typecheck`
- `make test`
- `make test-unit`
- `make test-integration`
- `make test-e2e`
- `make test-all`
- `make demo`

`make test-all` is the final local quality gate.

## Security rules
- API keys backend-only.
- Encrypt persisted credentials at rest.
- Mask secrets in logs and UI after save.
- Never serialize decrypted secrets into job payloads persisted in Redis if avoidable; pass provider configuration IDs and resolve secrets server-side.
- Validate uploaded files and enforce size/type limits.
- Sanitize user-provided markdown/HTML shown in UI.
- Protect ingestion APIs with workspace API keys/tokens.
- Add rate limiting where appropriate.
- Avoid logging full customer transcripts by default in server logs.

## Scope discipline
If a requested task conflicts with the core principles above, do not silently work around them. Implement the safer architecture and document the tradeoff.

Do not introduce unrelated frameworks, ORMs, state managers, or infrastructure unless needed. Prefer a small number of well-understood dependencies.
