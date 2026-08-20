# Development Architecture

The numbered specifications and `AGENTS.md` are authoritative. This guide explains the implemented boundaries.

## Request and execution flow

1. A workspace user or API key submits a canonical `ConversationTrace`.
2. The API validates it, stores the raw envelope and normalized immutable records, and rejects conflicting replays.
3. Creating an eval run snapshots trace hashes, evaluator definitions/versions, sampling, provider connection version, model, and routing profile.
4. Celery receives only the run ID. The worker resolves encrypted credentials server-side and reconstructs canonical evaluation context.
5. Separate specialist evaluators call `llm-gateway`; every structured response is JSON-Schema validated before persistence.
6. Failed results are clustered, root causes are synthesized, and recommendations enter `PENDING_REVIEW`.
7. A human may approve, reject, or edit. Only approved/edited versions can produce a draft artifact.

## Dependency rules

- `eval-core` imports canonical schemas and `llm-gateway`, never a vendor SDK/adapter.
- `llm-gateway` knows only the provider protocol and normalized request/response/error types.
- `llm-providers` contains provider-specific HTTP contracts.
- `connectors` are read-only normalizers. They return `ConversationTrace` and have no writeback method.
- `apps/web` calls versioned HTTP APIs and never receives a saved provider credential.

## Adding an evaluator

Create `evals/<id>/definition.yaml` and `prompt.md`, choose one specialist family, and add applicability/fixture tests. Evaluator output must match `JudgeOutput`; analytics must never parse judge prose. Root-cause and recommendation synthesis remain separate stages.

## Adding an LLM provider

Implement the complete gateway contract: connection test, optional model listing, text generation, structured generation, capability declaration, usage normalization, and safe error normalization. Register the adapter in the provider factory and add HTTP contract tests using a mock transport.

## Database changes

Change SQLAlchemy models, create an Alembic revision, check upgrade and downgrade on SQLite and PostgreSQL, and add workspace-isolation tests. Source traces are append-only; derived results may be recomputed.
