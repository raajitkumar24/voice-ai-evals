# Canonical Data Contracts

Use Pydantic models as the executable source of truth and generate JSON Schemas/OpenAPI from them. The examples below define required semantics, not necessarily final field casing.

## 1. ConversationTrace

```json
{
  "schema_version": "1.0",
  "conversation_id": "conv_123",
  "agent_id": "agent_1",
  "agent_config_version_id": "cfg_17",
  "started_at": "2026-08-20T10:00:00Z",
  "ended_at": "2026-08-20T10:04:32Z",
  "channel": "voice",
  "metadata": {
    "campaign_id": "cmp_12",
    "external_conversation_id": "abc",
    "tags": ["collections"]
  },
  "language_summary": {
    "primary_language": "hi",
    "languages": ["hi", "en"],
    "code_switching": true
  },
  "turns": [],
  "retrieval_events": [],
  "tool_calls": [],
  "outcome": {
    "goal_achieved": false,
    "disposition": "callback_requested"
  }
}
```

## 2. Turn

```json
{
  "turn_id": "turn_12",
  "sequence": 12,
  "timestamp_ms": 92000,
  "speaker": "CUSTOMER",
  "text_original": "Mera outstanding amount kitna hai?",
  "language": {
    "code": "hi-Latn",
    "confidence": 0.94,
    "code_switched": true
  },
  "translation": {
    "language": "en",
    "text": "How much is my outstanding amount?",
    "generated_by": "optional"
  }
}
```

`translation` is optional and never replaces `text_original`.

Speaker enum at minimum:
- CUSTOMER
- AGENT
- HUMAN_AGENT
- SYSTEM
- UNKNOWN

## 3. AgentConfigurationVersion

```json
{
  "id": "cfg_17",
  "agent_id": "agent_1",
  "version": "17",
  "prompt": "...",
  "model": {
    "provider": "openai",
    "model": "configured-model",
    "parameters": {
      "temperature": 0.2
    }
  },
  "tool_definition_version_ids": ["tooldef_1_v3"],
  "knowledge_source_version_ids": ["kb_1_v12"],
  "retrieval_config": {
    "top_k": 5,
    "search_type": "hybrid"
  },
  "created_at": "..."
}
```

Production agent model metadata is descriptive; it does not determine which model judges the eval.

## 4. RetrievalEvent

```json
{
  "retrieval_event_id": "ret_14",
  "timestamp_ms": 93000,
  "trigger_turn_id": "turn_12",
  "query_original": "Mera outstanding amount kitna hai?",
  "query_rewritten": "customer outstanding account balance",
  "retriever": {
    "type": "hybrid",
    "top_k": 5,
    "threshold": 0.7
  },
  "chunks": [
    {
      "chunk_id": "chunk_88",
      "source_id": "kbdoc_5",
      "content": "...",
      "rank": 1,
      "score": 0.86,
      "metadata": {
        "title": "Loan FAQ",
        "section": "Outstanding Balance"
      }
    }
  ]
}
```

## 5. ToolDefinitionVersion

```json
{
  "id": "tooldef_check_eligibility_v3",
  "name": "check_eligibility",
  "description": "Checks preliminary eligibility after required customer facts are collected.",
  "input_schema": {
    "type": "object",
    "properties": {
      "salary": {"type": "number"},
      "employment_type": {"type": "string"}
    },
    "required": ["salary", "employment_type"]
  },
  "policy": {
    "preconditions": [
      "salary_confirmed",
      "employment_type_confirmed"
    ]
  }
}
```

## 6. ToolCall

```json
{
  "tool_call_id": "tc_123",
  "tool_definition_version_id": "tooldef_check_eligibility_v3",
  "trigger_turn_id": "turn_18",
  "timestamp_ms": 142000,
  "arguments": {
    "salary": 50000,
    "employment_type": "salaried"
  },
  "argument_provenance": {
    "salary": {"source": "conversation", "turn_id": "turn_15"},
    "employment_type": {"source": "conversation", "turn_id": "turn_17"}
  },
  "status": "SUCCESS",
  "result": {
    "eligible": true,
    "max_amount": 300000
  },
  "duration_ms": 410
}
```

Tool status:
- SUCCESS
- ERROR
- TIMEOUT
- CANCELLED

## 7. KnowledgeSourceVersion
Must record source/version lineage. V1 types:
- TEXT
- MARKDOWN
- PDF
- DOCX
- URL_SNAPSHOT
- FAQ_JSON

Store parsed text/chunks separately from source metadata.

## 8. EvalDefinition

```yaml
id: no_guaranteed_approval
version: 1
name: No guaranteed approval
family: RUBRIC
scope: CONVERSATION
severity: CRITICAL
rubric: |
  The agent must never state or imply that final loan approval is guaranteed.
applicability: |
  Apply when approval, eligibility, sanction, or loan confirmation is discussed.
output_schema: rubric_result_v1
```

## 9. EvalSuite

```json
{
  "id": "suite_default_v1",
  "name": "Default Voice Agent Suite",
  "eval_definition_versions": [
    "response_quality_v1",
    "grounding_v1",
    "rag_v1",
    "tool_trajectory_v1",
    "conversation_quality_v1"
  ],
  "thresholds": {
    "critical_failure_rate_max": 0.01
  }
}
```

## 10. EvalRun
Must persist:
- dataset snapshot id;
- suite/version;
- evaluator routing profile/version;
- sampling config;
- timestamps/status;
- counts;
- usage/cost totals;
- warnings/errors.

## 11. EvalResult

```json
{
  "id": "evalres_1",
  "eval_run_id": "run_1",
  "conversation_id": "conv_123",
  "turn_id": "turn_22",
  "evaluator_id": "grounding",
  "evaluator_version": "1",
  "verdict": "FAIL",
  "confidence": 0.96,
  "severity": "CRITICAL",
  "failure_code": "CLAIM_CONTRADICTED_BY_TOOL",
  "reason": "Agent stated 500000 while the tool returned 300000.",
  "evidence": [
    {"type": "TURN", "id": "turn_22"},
    {"type": "TOOL_CALL", "id": "tc_123"}
  ],
  "judge_provenance": {
    "provider": "anthropic",
    "model": "configured-model",
    "routing_profile_version": "profile_3",
    "fallback_used": false
  },
  "usage": {
    "input_tokens": 1200,
    "output_tokens": 180,
    "latency_ms": 1900
  }
}
```

## 12. Finding
A Finding is a clustered systemic issue.

Required fields:
- title;
- summary;
- severity;
- root_cause_owner;
- confidence;
- failure codes;
- affected conversation count;
- affected rate;
- language distribution;
- first/last observed;
- trend;
- representative evidence;
- status: OPEN | REVIEWING | MITIGATED | DISMISSED.

## 13. Recommendation / ChangeProposal

```json
{
  "id": "rec_142",
  "finding_id": "finding_7",
  "status": "PENDING_REVIEW",
  "change_type": "PROMPT_PATCH",
  "summary": "Prevent guaranteed approval language.",
  "target": {
    "type": "AGENT_PROMPT",
    "version_id": "cfg_17",
    "section_hint": "Eligibility"
  },
  "current_content": "Tell eligible customers they qualify.",
  "proposed_content": "...",
  "rationale": "...",
  "confidence": 0.94,
  "requires_business_fact_verification": false,
  "regression_run_id": "regrun_8"
}
```

Change types:
- PROMPT_PATCH
- KB_GAP
- KB_CONTENT_PATCH
- RETRIEVAL_CONFIG_CHANGE
- TOOL_DESCRIPTION_PATCH
- TOOL_SCHEMA_PATCH
- TOOL_POLICY_PATCH
- LLM_CONFIG_CHANGE
- DATA_QUALITY_FIX
- HUMAN_INVESTIGATION

`KB_GAP` may have no proposed factual content.

## 14. HumanReview
Record:
- reviewer;
- action;
- timestamp;
- optional edited proposal;
- comment;
- source recommendation version.

Actions:
- APPROVE
- REJECT
- EDIT_AND_APPROVE
- MARK_NOT_ISSUE
- REQUEST_MORE_REVIEW

## 15. API compatibility/versioning
All public ingestion payloads include `schema_version`.
Breaking canonical schema changes require a new major schema version and migration/compatibility logic where feasible.
