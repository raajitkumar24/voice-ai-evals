# Product Specification — Voice AI Evals

## 1. Product vision
Voice AI Evals is an open-source, self-hostable evaluation and observability platform for production Voice AI agents.

It helps teams answer:
- How well is my agent performing?
- What is failing?
- Which layer caused the failure?
- What evidence supports that diagnosis?
- What should I change?
- Does the proposed change improve performance without causing regressions?

The product is not an autonomous configuration editor. It is an evidence-backed reviewer and recommendation system with mandatory human approval.

## 2. Target users
Primary:
- Head of AI Product / Product Manager
- AI/ML Engineer
- Conversation Designer / Prompt Engineer
- Voice AI Platform Engineer

Secondary:
- QA / Compliance reviewers
- Knowledge managers
- Engineering managers
- Operations teams

## 3. Core use cases
### 3.1 Response and prompt evaluation
Evaluate agent responses against configurable rubrics; cluster systemic failures; recommend exact minimal prompt patches.

### 3.2 Hallucination and grounding
Decompose factual agent responses into claims and classify each as supported, partially supported, unsupported, contradicted, or unverifiable using allowed evidence sources.

### 3.3 RAG/knowledge evaluation
Identify whether failures come from:
- missing knowledge;
- retrieval miss;
- poor ranking;
- low precision/noisy context;
- conflicting knowledge;
- correct retrieval but poor context utilization.

### 3.4 Tool trajectory evaluation
Evaluate:
- correct tool selection;
- correct invocation timing;
- argument completeness/correctness/provenance;
- tool result interpretation/use;
- end-to-end trajectory validity.

### 3.5 Voice conversation behavior
Evaluate transcript-observable conversation quality:
- relevance;
- conciseness for voice;
- acknowledgement;
- clarification;
- repetition;
- objection handling;
- conversation progression;
- premature ending;
- recovery after misunderstanding;
- code-switch handling.

Audio-native metrics are a future extension and are not required for V1 unless trace data is provided.

### 3.6 Root-cause synthesis
Combine specialist evaluator outputs into a primary root cause, secondary effects, confidence, and recommended remediation class.

### 3.7 Human-reviewed recommendations
Generate clustered Change Proposals with:
- issue summary;
- evidence;
- root cause;
- proposed change/diff;
- confidence;
- historical affected calls;
- regression-test results;
- risks;
- review status.

Humans approve/edit/reject. Approved changes create/export draft patch artifacts only.

## 4. Product principles
- Provider agnostic
- Voice-platform agnostic
- Multilingual by default
- Human-controlled remediation
- Evidence-linked diagnosis
- Reproducible eval runs
- Transparent judge provenance
- Cost-aware execution
- Self-hostable
- API-first + UI + CLI

## 5. Input resources
The platform must support ingesting:
1. Agent prompt/configuration
2. Knowledge base source documents/content
3. Diarized timestamped call transcripts
4. Retrieval traces/chunks
5. Tool definitions
6. Tool call logs and outputs
7. LLM settings used by the production voice agent
8. Conversation outcomes/metadata where available

Not every integration supplies every field. The UI must show integration/eval coverage and gracefully degrade.

## 6. Integration maturity levels
### Level 1 — Transcript Eval
Required:
- transcript;
- agent prompt.

Unlocks:
- rubric evals;
- conversation quality;
- limited grounding where evidence is available.

### Level 2 — Grounded/RAG Eval
Adds:
- KB;
- retrieval traces.

Unlocks:
- knowledge coverage;
- retrieval diagnostics;
- stronger grounding evaluation.

### Level 3 — Full Agent Trace
Adds:
- tool definitions/calls/results;
- LLM configuration;
- conversation state and dynamic variables when available.

Unlocks:
- tool trajectory;
- stronger root-cause attribution;
- configuration intelligence.

## 7. Evaluation modes
### Production evals
Evaluate imported/streamed real calls. Support random and stratified sampling.

### Offline regression evals
Run existing eval cases against current vs candidate configurations/patches.

### Pre-release suites
Allow teams to define thresholds and block their own release process externally through CLI exit codes/API results. The Evals platform itself does not publish agents.

## 8. Core entities
- Workspace
- User
- AI Provider Connection
- Agent
- Agent Configuration Version
- Conversation
- Turn
- Retrieval Event
- Retrieved Chunk
- Tool Definition
- Tool Call
- Knowledge Source
- Eval Definition
- Rubric
- Eval Suite
- Dataset
- Eval Run
- Eval Result
- Finding
- Recommendation / Change Proposal
- Candidate Patch
- Regression Run
- Human Review

## 9. Primary metrics
### Executive metrics
- Eval Pass Rate
- Critical Failure Rate
- Grounded Response Rate
- Tool Execution Accuracy
- Knowledge Coverage
- Conversation Quality
- Eval Coverage
- Language Performance Gap

### Risk metrics
- Unsupported Claim Rate
- Contradicted Claim Rate
- Critical Hallucination Rate
- Critical Compliance Failure Rate
- Unsafe/incorrect tool action rate

### RAG metrics
- Knowledge Coverage
- Retrieval Recall
- Retrieval Precision
- Context Utilization Rate
- Knowledge Conflict Rate

### Tool metrics
- Correct Tool Selection
- Correct Tool Timing
- Argument Accuracy
- Result Utilization
- Complete Trajectory Success

### Eval-system health
- Judge confidence distribution
- Human/judge agreement where labels exist
- Judge disagreement rate
- Provider request success rate
- Eval latency
- Eval cost per conversation

## 10. Severity
Default severity enum:
- INFO
- LOW
- MEDIUM
- HIGH
- CRITICAL

Severity is independent of confidence.

## 11. Verdict
All evaluators use:
- PASS
- FAIL
- NOT_APPLICABLE
- UNCERTAIN

Avoid fake precision with arbitrary 1–5 scores as the primitive. Aggregate metrics may derive percentages from verdicts.

## 12. Failure ownership taxonomy
- PROMPT
- KNOWLEDGE_CONTENT
- RETRIEVAL
- TOOL_SELECTION
- TOOL_TIMING
- TOOL_ARGUMENTS
- TOOL_EXECUTION
- TOOL_RESULT_USAGE
- MODEL
- LLM_CONFIGURATION
- CONVERSATION_POLICY
- DATA
- TRANSCRIPTION_OR_LANGUAGE
- UNKNOWN

## 13. Multilingual requirements
- Same rubric semantics across languages.
- Original transcript is canonical evidence.
- Optional reviewer translation.
- Per-turn language detection metadata.
- Support code-switching.
- Language filters on all relevant dashboards.
- Language parity analytics with minimum sample thresholds.
- Do not conclude language degradation solely from low-volume raw averages.
- Test English, Hindi, Hinglish, Tamil, Malayalam in V1 fixtures.

## 14. Recommendation safeguards
The product must never automatically:
- update a production prompt;
- add/delete KB content;
- update tool definitions;
- change model settings;
- publish a new agent version.

Recommendation actions in V1:
- Review
- Edit
- Approve
- Reject
- Mark not an issue
- Copy patch
- Export patch/report
- Add confirmed failure to regression dataset

## 15. Out of scope for V1
- Autonomous writeback to production agent platforms
- Full audio/prosody analysis requiring raw waveform ML pipelines
- Native integrations with every commercial voice-agent vendor
- Automated business-fact generation for missing KB content
- Fine-tuning models
- Billing/paid SaaS infrastructure

## 16. V1 success criteria
A fresh user can clone the repo, run Docker Compose, connect any one supported LLM provider, load the multilingual demo dataset, run the default suite, see intentionally seeded failures correctly grouped, inspect evidence, receive safe recommendations, and run regression comparisons—all without modifying source code.
