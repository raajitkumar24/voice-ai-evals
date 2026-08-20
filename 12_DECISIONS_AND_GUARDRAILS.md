# Architecture Decisions and Guardrails

These decisions are intentionally pre-made so Codex does not repeatedly revisit them.

## ADR-001: Human-in-the-loop recommendations
Decision: no automatic production configuration mutation in V1.
Reason: recommendations may introduce regressions and enterprise users need control/auditability.

## ADR-002: Canonical trace first
Decision: normalize every external source into canonical schemas before eval.
Reason: keeps eval core independent of voice-agent vendors.

## ADR-003: LLM Gateway
Decision: all judge calls go through a provider-neutral gateway.
Reason: users choose OpenAI/Anthropic/Gemini/local; evaluator code remains unchanged.

## ADR-004: Original language is source of truth
Decision: do not make English translation mandatory for eval.
Reason: translation can lose meaning; platform must provide equivalent semantics across languages.

## ADR-005: Specialist judges
Decision: separate response, grounding, RAG, tool, conversation, root-cause, recommendation evaluators.
Reason: improves diagnosability and testability.

## ADR-006: Structured outputs
Decision: all evaluator outputs schema-validated.
Reason: reliable analytics and versioning.

## ADR-007: Immutable raw traces
Decision: ingestion source facts immutable except administrative deletion/retention operations.
Reason: auditability/re-evaluation.

## ADR-008: Findings are clustered issues
Decision: UI operational object is systemic Finding, not every individual EvalResult.
Reason: users need actionable patterns rather than noise.

## ADR-009: CLI and API are first-class
Decision: UI is not the only product interface.
Reason: open-source developers need automation/CI.

## ADR-010: Paid LLM calls not required for CI
Decision: deterministic TestLLMProvider for automated tests.
Reason: forks/PRs must test without secrets or API cost.
