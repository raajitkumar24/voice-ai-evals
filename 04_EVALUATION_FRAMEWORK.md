# Evaluation Framework Specification

## 1. Architecture
Use specialist evaluators rather than one monolithic judge. Each evaluator:
- receives a typed input bundle;
- checks applicability;
- calls LLM only when needed;
- returns schema-validated structured output;
- includes evidence and provenance;
- can be versioned independently.

## 2. Response/Rubric evaluator
### Inputs
- relevant turn/window/conversation;
- agent prompt/config;
- rubric definition;
- language metadata.

### Output
- verdict;
- confidence;
- severity;
- explanation;
- evidence turn IDs;
- rubric-specific failure code.

### Default rubric dimensions
- instruction adherence
- correctness
- relevance
- voice conciseness
- conversation progression
- objection handling
- compliance
- confirmation behavior
- repetition
- personalization correctness
- tone/appropriateness
- goal adherence

Do not force all rubrics on all calls. Applicability must be explicit.

## 3. Grounding/hallucination evaluator
### Evidence hierarchy
Potential evidence sources:
- system/agent prompt constants;
- knowledge base;
- retrieved chunks;
- customer/CRM variables supplied in trace;
- tool outputs;
- conversation history;
- deterministic platform facts supplied as evidence.

### Claim verdict
For each material factual claim:
- SUPPORTED
- PARTIALLY_SUPPORTED
- UNSUPPORTED
- CONTRADICTED
- UNVERIFIABLE

### Failure codes
Examples:
- CLAIM_UNSUPPORTED
- CLAIM_CONTRADICTED_BY_KB
- CLAIM_CONTRADICTED_BY_TOOL
- CLAIM_CONTRADICTED_BY_CUSTOMER_DATA
- ACCOUNT_SPECIFIC_FACT_WITHOUT_TOOL
- CRITICAL_FINANCIAL_CLAIM_UNGROUNDED

Severity must consider claim category; wrong pricing/payment/eligibility/policy may be high or critical.

## 4. RAG evaluator
Separate:
### Knowledge availability
Does the available knowledge contain the answer needed?
Failure: `KNOWLEDGE_GAP`

### Retrieval recall
Was relevant knowledge retrieved when it existed?
Failure: `RETRIEVAL_MISS`

### Ranking
Was relevant content beyond top-k / ranked too low?
Failure: `RETRIEVAL_RANKING_FAILURE`

### Precision
Was context dominated by irrelevant chunks?
Failure: `LOW_CONTEXT_PRECISION`

### Conflict
Did retrieved/source knowledge conflict?
Failure: `KNOWLEDGE_CONFLICT`

### Utilization
Did agent ignore/misuse correct retrieved context?
Failure: `CONTEXT_UTILIZATION_FAILURE`

### Outputs
Include source/chunk IDs and whether recommended remediation is knowledge-content, retrieval-config, or prompt/context-use related.

## 5. Tool trajectory evaluator
Evaluate at four levels:
1. Tool selection
2. Tool timing/preconditions
3. Argument correctness/provenance
4. Tool result utilization

### Failure codes
- REQUIRED_TOOL_NOT_CALLED
- WRONG_TOOL_SELECTED
- UNNECESSARY_TOOL_CALLED
- TOOL_CALLED_TOO_EARLY
- TOOL_CALLED_TOO_LATE
- TOOL_CALLED_AFTER_UNGROUNDED_RESPONSE
- MISSING_ARGUMENT
- INCORRECT_ARGUMENT
- FABRICATED_ARGUMENT
- STALE_ARGUMENT
- WRONG_ARGUMENT_SOURCE
- ARGUMENT_FORMAT_ERROR
- TOOL_RESULT_IGNORED
- TOOL_RESULT_MISINTERPRETED
- TOOL_ERROR_NOT_HANDLED

Trajectory evaluator must know which tools were available at that point; never penalize for an unavailable tool.

## 6. Conversation behavior evaluator
Transcript-level V1 checks:
- over-verbosity for voice;
- unnecessary repetition;
- acknowledgement;
- clarification after ambiguity;
- handling of “sorry/repeat”;
- respectful refusal/end;
- objection handling;
- customer intent continuity;
- premature termination;
- turn-to-turn coherence;
- code-switching handling.

When transcript evidence is insufficient (e.g., prosody), return NOT_APPLICABLE rather than guessing.

## 7. Root Cause Synthesizer
### Inputs
All applicable specialist results + relevant configuration evidence.

### Required output
- primary root cause owner;
- primary failure code;
- secondary effects;
- confidence;
- evidence references;
- explicitly ruled-out causes where useful;
- recommended remediation class;
- whether more human investigation is required.

Example:
- Primary: RETRIEVAL / RETRIEVAL_MISS
- Secondary: hallucination after missing context
- Not root cause: prompt
- Action: improve retrieval/index/query rewriting

## 8. Recommendation engine
Generate the smallest safe change proposal.

### Minimal Patch Principle
Prefer localized change over prompt bloat.

### Remediation precedence
Consider in this order where appropriate:
1. deterministic validation/business rule
2. tool policy/required grounding
3. retrieval configuration
4. missing/incorrect knowledge
5. localized prompt change
6. model/LLM configuration
7. human process/data fix

### Guardrails
- Never invent missing business facts.
- KB gap with unknown answer => describe what information is missing and request verification.
- Every recommendation links to evidence and affected volume.
- Low-confidence findings should recommend investigation rather than a concrete patch when unsafe.

## 9. Finding clustering
Cluster repeated results into systemic Findings.

Preferred approach:
1. deterministic grouping on evaluator/failure code/target;
2. optional embedding/LLM-assisted semantic grouping within that safe bucket;
3. representative examples chosen by diversity and severity.

Avoid merging semantically distinct issues solely because text looks similar.

## 10. Judge confidence
Confidence is evaluator certainty, not severity.

Suggested interpretation:
- >=0.85: High
- 0.65–0.849: Medium
- <0.65: Low

Thresholds configurable.
Low confidence may create UNCERTAIN verdict and review queue entry.

## 11. Multi-judge mode
Optional per eval definition:
- single judge;
- verify-failures with second judge;
- N-judge consensus for critical rubrics.

Persist individual votes and consensus rule.
If disagreement exceeds configured threshold, mark for human review.

## 12. Two-stage evaluation
Optional cost-control pipeline:
- Stage 1 inexpensive screening model;
- Stage 2 stronger verifier for suspected failures/high-risk cases.

Never hide which model produced final verdict.

## 13. Multilingual evaluation contract
- Evaluate original text directly with multilingual-capable judge where possible.
- Translation is optional supporting context, not canonical evidence.
- Rubric meaning is language-independent.
- Store judge language-capability metadata.
- Language-sensitive/ambiguous verdicts may request human review with language proficiency note.

## 14. Eval reproducibility
Eval result identity must be reproducible from:
- input trace snapshot;
- evaluator version;
- rubric version;
- provider/model;
- judge configuration;
- prompt/template version;
- sampling config.

Do not overwrite historical EvalResults after evaluator upgrades; create new runs.

## 15. Default eval suite
Ship a demo/default suite with:
- response quality
- instruction adherence
- grounding
- knowledge/retrieval
- tool trajectory
- conversation quality

Root cause and recommendation run only on failures/findings.
