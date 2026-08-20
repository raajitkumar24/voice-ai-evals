# Test Strategy

## 1. Goals
Tests must verify not only UI functionality but core trust properties:
- provider neutrality;
- multilingual semantic parity;
- correct failure attribution;
- evidence linkage;
- human approval safety;
- reproducibility;
- secret handling;
- workspace isolation.

## 2. Test layers
### Unit
- Pydantic validation
- metric formulas
- severity/risk derivation
- language sample thresholds
- provider error normalization
- clustering helpers
- recommendation state machine
- cost aggregation

### Contract tests
Every provider adapter runs the same test contract using mocked HTTP/SDK responses:
- connection test
- plain generation
- structured generation
- usage normalization
- timeout
- rate limit
- malformed structured output
- auth failure

Every connector adapter runs canonical mapping contract tests.

### Integration
With Postgres/Redis:
- ingestion persistence
- idempotency
- queue execution
- eval result storage
- run aggregation
- recommendation workflow
- workspace isolation

### Evaluator golden tests
Fixtures with human-authored expected labels. Avoid exact wording assertions; assert structured verdict/failure code/evidence/root cause.

Maintain:
`tests/fixtures/golden/`

### Frontend component tests
- filters
- charts data mapping
- diff view
- secret masking
- status components

### End-to-end
Playwright scenarios in `10_E2E_TEST_CASES.md`.

## 3. LLM test policy
CI must not require paid external LLM calls.
Use deterministic fake/mock provider implementing canonical LLM interface for most tests.

Optional live-provider tests:
- marked `live_provider`
- run only when matching env credentials exist
- never run by default in forks/PRs

## 4. Deterministic fake judge
Create a `TestLLMProvider` available only in test/dev demo mode that returns fixture-driven structured outputs. This makes E2E reliable without spending API credits.

Production builds must not accidentally use TestLLMProvider unless explicit development/test flag is enabled.

## 5. Multilingual golden dataset
At minimum include semantically equivalent behaviors:
- English
- Hindi Devanagari
- Hinglish Latin script
- Tamil
- Malayalam

For a shared rubric such as “never guarantee final approval,” all equivalent violating statements must yield FAIL with same failure taxonomy/severity.

Also include language-specific ambiguity leading to UNCERTAIN rather than forced FAIL/PASS.

## 6. RAG golden cases
- answer absent from KB => KNOWLEDGE_GAP
- answer in KB but absent retrieval => RETRIEVAL_MISS
- relevant chunk rank > configured top-k => RETRIEVAL_RANKING_FAILURE
- mostly irrelevant retrieval => LOW_CONTEXT_PRECISION
- conflicting chunks => KNOWLEDGE_CONFLICT
- correct chunk retrieved but agent contradicts => CONTEXT_UTILIZATION_FAILURE plus grounding issue

## 7. Tool golden cases
- correct tool/timing/args/result usage => PASS
- required tool omitted
- called before required data collected
- called after agent already invented result
- missing required argument
- fabricated argument
- stale argument
- result contradicted in response
- tool unavailable in trace => evaluator must not expect it

## 8. Recommendation safety tests
- unknown KB policy/value => recommendation says knowledge is missing, no invented value
- prompt issue => localized diff
- low confidence => investigation recommendation
- approval => no external writeback
- rejected => status/audit preserved

## 9. Security tests
- API key not returned from provider config GET
- API key not present in rendered HTML
- API key not logged during connection failure
- cross-workspace conversation access denied
- cross-workspace recommendation access denied
- ingestion key scope enforced
- path traversal upload blocked
- malicious markdown sanitized

## 10. Performance sanity
Not a full benchmark, but test:
- batch ingest 1,000 lightweight traces without timeout in local CI envelope
- queue can process concurrent eval tasks
- dashboard aggregate endpoints use DB aggregation/pagination rather than loading all conversations in memory

## 11. Acceptance gate
`make test-all` should run:
- lint
- typecheck
- unit
- integration
- non-live evaluator golden tests
- E2E

Live-provider tests are separate:
`make test-live-providers`
