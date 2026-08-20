# Integrations and LLM Provider Specification

## 1. Ingestion methods
### REST API
Primary production contract:
- POST conversation trace
- batch POST traces
- upsert agent config versions
- upsert tool definitions
- upload/register knowledge sources
- create retrieval events/tool calls if sent incrementally

All ingestion operations must be idempotent using external IDs/idempotency keys.

### Generic webhook
Events:
- conversation.started
- turn.completed
- retrieval.completed
- tool.called
- tool.completed
- conversation.completed

Reconstruct canonical trace safely even if events arrive slightly out of order. Persist raw webhook envelope for troubleshooting subject to retention policy.

### File import
V1:
- JSON
- JSONL
- CSV
- TXT transcript import

Include mapping wizard and saved Import Profiles.

### Connector SDK
Define interface to:
- fetch conversations
- fetch agent configs
- fetch KB/retrieval traces where supported
- fetch tool definitions/logs where supported

Core must not require native connectors.

## 2. LLM Gateway canonical request
Must support:
- system/developer instructions abstraction
- message/content array
- model id
- temperature/top-p where supported
- max output tokens
- structured output schema
- timeout
- metadata tags

Provider adapters translate unsupported parameters or reject clearly; never silently reinterpret material settings.

## 3. Provider interface
At minimum:

```python
class LLMProvider(Protocol):
    async def test_connection(self) -> ProviderHealth: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    async def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResponse: ...
    def capabilities(self, model: str | None = None) -> ProviderCapabilities: ...
```

## 4. Initial provider support
### OpenAI
API-key based server-side adapter.

### Anthropic
API-key based server-side adapter.

### Google Gemini
API-key based server-side adapter.

### OpenAI-compatible endpoint
Config:
- base URL
- optional API key
- model name
- capability overrides

### Ollama/local
Config:
- base URL
- model
No public credential required by default.

Do not hard-code current vendor model lists in source. Fetch where possible or allow manual model entry with capability validation.

## 5. Provider capabilities
Canonical flags:
- structured_output
- JSON mode
- long context
- multilingual
- tool/function calling
- vision (future)
- streaming (not required for evals)

Eval definitions can declare required capabilities.

## 6. Structured output
Evaluator code requests a canonical Pydantic/JSON schema.
Provider adapter is responsible for the strongest supported structured-output mechanism.
Gateway validates returned payload. On invalid payload:
1. retry based on policy;
2. optional repair attempt;
3. fail evaluator with canonical structured-output error.

Never accept invalid JSON into analytics.

## 7. Routing profiles
Example:
- default provider/model for all evaluators;
- override per evaluator family;
- screening model;
- verifier model;
- optional explicit fallback.

Persist routing profile version with eval run.

## 8. Fallback
Fallback is optional and never silent.
Trigger categories configurable:
- rate limit
- timeout
- transient provider 5xx

Do not fallback on authentication or malformed configuration by default.
Persist requested vs executed provider/model and reason.

## 9. Multi-judge consensus
Configurable for critical evals:
- providers/models list
- quorum rule
- disagreement threshold
- human-review-on-disagreement flag

## 10. Secrets
Support modes:
### Environment-only
Variables such as:
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY

### Encrypted DB
UI saves credential to backend; backend encrypts at rest using app encryption key.

Provider config stores secret reference, never plaintext credential.

## 11. Public SDK
Python SDK V1 minimum:
- create/upsert agent
- ingest conversation(s)
- create eval run
- poll/get run
- list findings
- export recommendations

Node SDK can be V1.1 if needed, but API examples must include curl.

## 12. CLI
Required commands:
- `voice-evals init`
- `voice-evals import <file>`
- `voice-evals run [--agent ... --suite ...]`
- `voice-evals runs list`
- `voice-evals findings list`
- `voice-evals serve` (optional wrapper if Docker/dev flow makes sense)

CLI must return non-zero exit code when a configured suite threshold is violated if invoked with a CI/gate flag.

## 13. Demo dataset
Ship `examples/loan-agent-demo` with:
- prompt
- tool definitions
- KB
- multilingual conversations
- retrieval traces
- tool calls
- expected seeded issues

Languages:
- English
- Hindi
- Hinglish
- Tamil
- Malayalam

Seed failures:
- guaranteed approval
- unsupported pricing/fee
- missing KB partial-prepayment knowledge
- retrieval miss despite source knowledge
- tool called too early
- wrong tool argument
- tool result contradicted by response
- repeated pitch after rejection
