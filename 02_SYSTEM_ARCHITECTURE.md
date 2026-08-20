# System Architecture

## 1. High-level architecture

```text
Voice AI / Files / REST / Webhooks
              |
              v
       Ingestion Gateway
              |
              v
        Normalization
              |
              v
     Canonical Trace Store
              |
              +-----------------------------+
              |                             |
              v                             v
        Eval Orchestrator              Knowledge Store
              |
              v
        Async Eval Queue
              |
              v
          Eval Workers
              |
      +-------+--------+----------+----------+----------+
      |                |          |          |          |
      v                v          v          v          v
 Rubric Judge      Grounding     RAG       Tools    Conversation
      \                |          |          |          /
       +---------------+----------+----------+---------+
                               |
                               v
                       Root Cause Synthesis
                               |
                               v
                      Recommendation Engine
                               |
                               v
                         Human Review UI
```

All LLM calls:

```text
Evaluator -> LLM Gateway -> Provider Registry -> Provider Adapter -> External/local LLM
```

## 2. Components
### 2.1 Web app
Responsibilities:
- onboarding;
- provider configuration;
- agent/data imports;
- dashboards;
- finding exploration;
- conversation timeline;
- rubric/suite configuration;
- recommendation review;
- regression comparison;
- admin/system health.

Must never receive decrypted provider keys after save.

### 2.2 API service
Responsibilities:
- REST ingestion endpoints;
- auth/workspace context;
- CRUD for domain entities;
- eval-run creation;
- recommendation actions;
- provider credential management;
- metrics query endpoints;
- OpenAPI docs.

### 2.3 Eval worker
Responsibilities:
- load immutable input snapshot;
- execute evaluator DAG;
- call LLM Gateway;
- validate structured outputs;
- persist eval results;
- synthesize findings;
- aggregate run metrics;
- update run status.

### 2.4 LLM Gateway
Responsibilities:
- provider-neutral request object;
- model/provider routing;
- capability checks;
- retries/backoff;
- structured-output handling;
- usage normalization;
- latency tracking;
- provider errors -> canonical errors;
- optional explicit fallback;
- cost estimation via pricing metadata where configured.

### 2.5 Provider adapters
Initial adapters:
- OpenAI
- Anthropic
- Google Gemini
- OpenAI-compatible
- Ollama/local

Adapters own SDK/API specifics only.

### 2.6 Connector layer
Initial:
- Generic REST ingestion
- Generic webhook ingestion
- JSON/JSONL/CSV upload
- connector SDK interface

Example provider-native connector can be added after core is stable.

### 2.7 Storage
PostgreSQL for normalized relational metadata/results.
Object/file storage abstraction for large KB/import assets:
- local filesystem default;
- S3-compatible later/optional.

Redis for async job queue/cache only; not source of truth.

## 3. Suggested monorepo

```text
voice-ai-evals/
├── apps/
│   ├── web/
│   └── api/
├── workers/
│   └── eval-worker/
├── packages/
│   ├── schemas/
│   ├── eval-core/
│   ├── llm-gateway/
│   ├── llm-providers/
│   │   ├── openai/
│   │   ├── anthropic/
│   │   ├── gemini/
│   │   ├── openai-compatible/
│   │   └── ollama/
│   ├── connectors/
│   └── sdk/
├── evals/
│   ├── response_quality/
│   ├── grounding/
│   ├── rag/
│   ├── tool_trajectory/
│   ├── conversation/
│   ├── root_cause/
│   └── recommendation/
├── docs/
├── examples/
│   └── loan-agent-demo/
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── migrations/
├── docker-compose.yml
├── Makefile
├── AGENTS.md
└── README.md
```

## 4. Evaluation execution model
### 4.1 Snapshot
Each Eval Run captures immutable references/versions for:
- dataset/conversations;
- agent configuration;
- rubrics/suite;
- evaluator versions;
- model routing profile;
- provider configuration version (not secret value);
- knowledge source versions.

### 4.2 Parallel specialist evaluators
Run only applicable evaluators based on available trace data.

Example dependency DAG:
- response quality: transcript + prompt
- grounding: agent response + evidence sources
- RAG: retrieval trace and/or KB
- tool trajectory: available tools + tool calls/results + transcript
- conversation behavior: transcript
- root cause: specialist results
- recommendations: root-cause findings

### 4.3 Finding synthesis
Do not create one Finding per failing result by default. Cluster equivalent failure signatures across calls using deterministic fields first, then semantic clustering when needed.

Finding identity should include:
- evaluator/failure code;
- likely root cause;
- affected prompt/tool/KB area where known;
- semantic issue cluster.

## 5. Evaluation sampling
Support:
- all calls;
- random sample;
- stratified by language;
- stratified by campaign/agent/version;
- risk-based oversampling;
- failed-outcome oversampling.

Persist sampling methodology in Eval Run metadata.

## 6. Regression architecture
A Candidate Patch is an isolated proposed change. Regression Run compares baseline vs candidate against a Dataset/Eval Suite.

For V1, candidate simulation may support prompt-based changes directly. KB/tool patches may be represented as candidate context/config overrides when enough information is available.

Regression results must expose:
- fixed historical failures;
- unchanged failures;
- newly failing cases;
- metric deltas;
- critical regressions.

## 7. Multi-tenant/workspace model
Even self-hosted V1 should use a Workspace abstraction to avoid schema redesign later.
All primary entities carry `workspace_id`.

Authentication may begin with local account/admin mode, but ingestion API keys must be workspace scoped.

## 8. Reliability
Eval Run states:
- CREATED
- QUEUED
- RUNNING
- PARTIALLY_COMPLETED
- COMPLETED
- FAILED
- CANCELLED

Individual evaluator failures should not necessarily fail the full run. Persist partial failures and retry safely/idempotently.

## 9. Observability
Log:
- run IDs;
- evaluator IDs;
- conversation IDs (or hashed where configured);
- provider/model identifiers;
- request latency;
- normalized provider errors;
- retry/fallback metadata.

Do not log credentials or full transcript bodies by default.

## 10. Extensibility
New providers, connectors, evaluators, metrics, and storage backends must be addable through registries/interfaces without editing unrelated core orchestration logic.
