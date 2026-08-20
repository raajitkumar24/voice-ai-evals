# End-to-End Test Cases

These are mandatory acceptance scenarios for the finished product. Implement them as automated Playwright/API tests where feasible. Use the deterministic TestLLMProvider for default CI, plus optional live-provider smoke tests.

## E2E-001 Fresh clone and boot
**Goal:** Validate self-hosted quickstart.

Preconditions: clean machine/container with Docker.

Steps:
1. Copy `.env.example` to `.env` with test-safe values.
2. Run `docker compose up -d --build`.
3. Wait for health checks.
4. Open web app.

Expected:
- Web loads without stack trace.
- API/DB/Redis/worker healthy.
- onboarding is shown for new workspace.

## E2E-002 Connect LLM provider
Steps:
1. Open Integrations/AI Providers.
2. Add TestLLMProvider in test mode (production UI uses supported real provider options).
3. Test connection.
4. Save.

Expected:
- Connection is shown Connected.
- Secret value is never redisplayed.
- Network GET response does not contain secret.

## E2E-003 Provider agnosticism
Run same golden eval dataset through provider adapter contract mocks for OpenAI, Anthropic, Gemini, OpenAI-compatible, Ollama.

Expected:
- Eval core receives identical canonical result shape.
- No evaluator implementation changes by provider.
- Provenance reflects actual provider/model.

## E2E-004 Import multilingual demo dataset
Steps:
1. Choose Try Sample Dataset.
2. Import demo.

Expected:
- Agent/config/KB/tools/conversations imported.
- English, Hindi, Hinglish, Tamil, Malayalam visible.
- Integration maturity = Level 3 for complete fixtures.
- Import summary counts match fixture manifest.

## E2E-005 Run default eval suite
Steps:
1. Start Default Voice Agent Suite on demo dataset.
2. Monitor progress.

Expected:
- Run transitions QUEUED -> RUNNING -> COMPLETED.
- Counts reconcile.
- Usage/latency captured.
- Overview populated.

## E2E-006 Multilingual semantic parity
Fixture contains the same prohibited guarantee in five languages.

Expected for each:
- verdict FAIL;
- severity CRITICAL;
- same semantic failure code;
- evidence references original-language turn;
- language metadata differs appropriately.

No translation is required for correctness.

## E2E-007 Code-switching conversation
Fixture: Hindi/English/Hinglish mixed turns.

Expected:
- call language summary shows code switching;
- per-turn language metadata persists;
- eval succeeds;
- user can view Original + English without losing original.

## E2E-008 Hallucination — unsupported claim
Fixture: agent invents a processing fee absent from prompt/KB/tool/customer data.

Expected:
- claim UNSUPPORTED;
- grounding result FAIL;
- finding includes evidence and expected grounding source if inferable;
- high/critical severity according to demo rubric.

## E2E-009 Hallucination — contradicted by tool
Fixture tool returns maximum eligibility 300000; agent says 500000.

Expected:
- claim CONTRADICTED;
- failure code CLAIM_CONTRADICTED_BY_TOOL;
- evidence links agent turn + tool call;
- root cause likely TOOL_RESULT_USAGE/grounding, not KB.

## E2E-010 Knowledge gap
Fixture customer asks partial-prepayment rules; KB has no policy.

Expected:
- KNOWLEDGE_GAP;
- Recommendation describes missing concepts;
- Recommendation does not invent fees/limits/business values;
- `requires_business_fact_verification=true` or equivalent.

## E2E-011 Retrieval miss
Fixture source KB contains answer; retrieval trace excludes relevant chunk.

Expected:
- RETRIEVAL_MISS;
- root cause RETRIEVAL;
- no prompt patch proposed as primary remediation.

## E2E-012 Context utilization failure
Relevant chunk retrieved; agent contradicts it.

Expected:
- CONTEXT_UTILIZATION_FAILURE;
- grounding failure also recorded;
- root-cause synthesis distinguishes secondary hallucination from retrieval quality.

## E2E-013 Tool called too early
Fixture requires salary + employment type; tool called after salary but before employment type.

Expected:
- TOOL_CALLED_TOO_EARLY;
- missing precondition evidence shown;
- tool timing metric decreases.

## E2E-014 Wrong tool argument
Fixture conversation says salary 50000; tool called with 15000.

Expected:
- INCORRECT_ARGUMENT;
- expected and actual values represented safely;
- argument provenance links source turn.

## E2E-015 Required tool not called before account-specific answer
Fixture customer asks outstanding amount; agent answers before account tool.

Expected:
- REQUIRED_TOOL_NOT_CALLED or TOOL_CALLED_AFTER_UNGROUNDED_RESPONSE as appropriate;
- grounding failure;
- root cause TOOL_SELECTION/TIMING.

## E2E-016 Conversation behavior — repeats pitch after rejection
Fixture customer clearly says not interested; agent restarts pitch.

Expected:
- objection/rejection handling FAIL;
- finding clusters equivalent failures across at least two languages;
- evidence preserved in original language.

## E2E-017 Finding clustering
Import 20 conversations with same guarantee issue and 5 distinct unrelated issues.

Expected:
- guarantee failures synthesize into one systemic Finding, not 20 rows;
- affected count = 20;
- representative examples include multiple languages when present.

## E2E-018 Root-cause prioritization
Fixture: retrieval misses answer, then agent hallucinates.

Expected:
- primary root cause RETRIEVAL;
- hallucination recorded as secondary effect;
- recommendation focuses on retrieval, not generic “never hallucinate” prompt patch.

## E2E-019 Recommendation human review
Steps:
1. Open a generated prompt recommendation.
2. Review evidence/diff.
3. Approve.

Expected:
- status becomes APPROVED;
- audit event created;
- export/copy draft available;
- no external agent configuration changes.

## E2E-020 Edit and approve recommendation
Steps:
1. Edit proposed patch.
2. Approve edited version.

Expected:
- original AI proposal retained in history;
- human-edited proposal version stored;
- audit identifies edit + approval.

## E2E-021 Reject recommendation
Expected:
- status REJECTED;
- finding remains available;
- rejection reason optional/recorded if entered;
- no config change.

## E2E-022 Regression test fixes issue
Candidate prompt patch should fix guarantee cases.

Expected:
- baseline vs candidate metrics displayed;
- historical failures fixed count > 0;
- recommendation review shows impact.

## E2E-023 Regression test exposes new failure
Candidate patch intentionally makes responses over-verbose.

Expected:
- newly failing conversation-quality cases shown;
- candidate is not represented as risk-free;
- new critical regression (if seeded) prominently blocks “safe” status.

## E2E-024 Language performance dashboard
Fixture distributions produce lower Hinglish score with adequate sample.

Expected:
- performance-by-language table correct;
- gap shown;
- clicking Hinglish filters findings/conversations.

## E2E-025 Insufficient language sample
Fixture language with < configured minimum sample.

Expected:
- warning shown;
- no strong degradation conclusion;
- raw metrics still available with denominator.

## E2E-026 Eval coverage
Use Level 1 traces missing retrieval/tools.

Expected:
- response/conversation evals run;
- RAG/tool evals NOT_APPLICABLE or skipped with reason;
- Integration/Eval Coverage clearly states missing inputs and unlock path.

## E2E-027 Provider failure and explicit fallback
Configure primary TestProvider to rate-limit, fallback provider succeeds.

Expected:
- run completes when fallback allowed;
- result provenance shows requested/executed provider and fallback reason;
- no silent model substitution.

## E2E-028 Provider auth failure
Primary provider returns auth error.

Expected:
- no fallback by default;
- clear provider connection/run error;
- credential never logged/rendered.

## E2E-029 Structured output recovery
Provider first returns malformed output then valid output on allowed retry.

Expected:
- invalid payload never stored as EvalResult;
- retry metadata recorded;
- final structured result valid.

## E2E-030 Workspace isolation
Create Workspace A/B. Attempt to access A conversation/findings with B credentials.

Expected: denied/not found; no data leakage.

## E2E-031 Ingestion idempotency
Send same conversation payload twice with same external ID/idempotency key.

Expected: one canonical conversation, no duplicated turns/tool calls.

## E2E-032 Out-of-order webhook reconstruction
Send tool.completed before delayed tool.called/turn event fixture.

Expected: event staging/reconciliation eventually creates correct canonical trace or surfaces recoverable integrity warning; no silent data loss.

## E2E-033 CLI import and run
Steps:
1. `voice-evals import examples/.../conversations.jsonl`
2. `voice-evals run --suite default ...`

Expected:
- commands succeed;
- run ID printed;
- findings retrievable via CLI/API.

## E2E-034 CI threshold exit code
Run CLI with gate flag against failing demo suite.

Expected:
- non-zero exit when configured critical threshold violated;
- human-readable summary printed.

## E2E-035 Cost/usage analytics
Run fixtures with mocked provider usage.

Expected:
- request counts/token totals aggregate correctly;
- cost displayed only when pricing metadata exists;
- “unknown/not available” used rather than fabricated cost.

## E2E-036 Secret redaction
Force provider error containing echoed credential in mocked upstream payload.

Expected:
- application logs/API/UI redact secret.

## E2E-037 No production writeback invariant
Inspect public connector interface/routes and exercise recommendation approval.

Expected:
- no endpoint/method publishes or mutates external production agent configuration;
- only export/copy/draft artifact behavior exists.

## E2E-038 Original transcript preservation
Import translated and original fields.

Expected:
- original is immutable and displayed as source evidence;
- toggling translation never alters stored original.

## E2E-039 Eval version reproducibility
Run same dataset with evaluator v1, then evaluator v2.

Expected:
- historical v1 results remain unchanged;
- both runs show distinct evaluator version provenance.

## E2E-040 Complete demo acceptance
From a fresh environment:
1. boot stack;
2. load demo;
3. run default suite;
4. view overview;
5. inspect one prompt issue, one RAG issue, one tool issue;
6. open multilingual evidence;
7. review recommendation;
8. run regression comparison;
9. approve recommendation as draft/export;
10. run `make test-all`.

Expected: all core product promises demonstrated with no manual DB changes or source edits.
