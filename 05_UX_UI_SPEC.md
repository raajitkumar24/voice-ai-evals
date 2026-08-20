# UX / UI Specification

## 1. Navigation
Primary left navigation:
- Overview
- Findings
- Conversations
- Knowledge & Retrieval
- Tools
- Recommendations
- Eval Runs
- Eval Setup
- Integrations
- Settings

## 2. First-run onboarding
### Step 1 — Connect an AI Provider
Choices:
- OpenAI
- Anthropic
- Google Gemini
- OpenAI-compatible
- Ollama/local

Fields are provider-specific; all credentials masked after save.
Actions: Test connection, Save.

### Step 2 — Add an Agent/Data Source
Choices:
- Upload data
- REST API
- Webhook
- Try sample dataset
- Native connector (if installed)

### Step 3 — Map/import configuration
Prompt, tools, KB, model metadata, transcript/retrieval/tool fields.
Show Integration Maturity Level and missing data.

### Step 4 — Choose eval suite
Default Voice Agent Suite selected.

### Step 5 — Run eval
After run, land on a populated Overview with “Top issues requiring attention.”

## 3. Overview
Header:
- Agent selector
- date range
- eval run/dataset context
- filter button
- evaluated calls / eligible calls / coverage
- languages detected

### 3.1 Top-level health
Keep Quality and Risk separate.
- Agent Quality: percentage
- Agent Risk: LOW/MEDIUM/HIGH/CRITICAL based on configurable critical/high-risk thresholds

### 3.2 KPI cards
- Eval Pass Rate
- Critical Failure Rate
- Grounded Response Rate
- Tool Execution Accuracy
- Knowledge Coverage
- Conversation Quality
- Eval Coverage

Each card: value, delta, sample denominator, click-through.

### 3.3 Performance trend
Line chart with metric selector.
Overlay configuration/version markers where known.

### 3.4 Needs Attention
Rank findings by severity x affected volume x recency/trend.
Card fields:
- severity
- title
- affected calls/rate
- root cause
- trend
- confidence
- languages affected
- recommendation status

### 3.5 Failure ownership
Horizontal bars for root-cause owners.

### 3.6 Performance by language
Table/chart:
- language
- evaluated calls
- pass rate
- critical failure rate
- grounded rate
- tool accuracy
- sample confidence warning

Show language performance gap only for sufficiently sampled segments.

## 4. Findings page
Cluster-level rows, not individual failed calls.
Columns:
- severity
- finding
- root cause
- affected calls
- rate
- trend
- confidence
- recommendation state
- status

Filters:
- severity
- root cause
- evaluator/rubric
- language
- agent version
- production model metadata
- campaign
- outcome
- date
- finding status
- confidence

## 5. Finding detail
### Header
Title, severity, root cause, affected count/rate, trend, confidence.

### Section A — What is happening?
Short synthesized explanation and pattern frequency.

### Section B — Evidence
Representative transcript snippets linked to conversation/turn IDs.
Original language always visible.
Translation display modes:
- Original
- Original + English
- English only (still indicate original is source of truth)

### Section C — Why it is happening
Root cause, secondary effects, evidence, ruled-out causes where available.

### Section D — Recommended action
Recommendation summary and target.

### Section E — Impact
Affected scenarios, languages, campaigns, versions.

## 6. Conversation Explorer
Table:
- conversation ID
- language(s)
- campaign/tag
- duration
- eval pass rate
- critical issues
- grounding status
- tool status
- outcome

Click -> Conversation Eval Timeline.

## 7. Conversation Eval Timeline
Transcript centered chronologically.
Turn annotations aligned visually:
- rubric failure
- hallucination
- retrieval event
- tool call
- tool failure
- evidence source
- severity

Clicking an annotation opens evaluator details and evidence.

Evidence panel can show:
- Prompt
- KB/retrieved chunks
- Tool output
- Customer variables
- Conversation history

## 8. Grounding/Hallucination analytics
Cards:
- Grounded Response Rate
- Unsupported Claim Rate
- Contradicted Claim Rate
- Critical Hallucination Rate

Breakdowns:
- claim category
- expected evidence source
- language
- version

## 9. Knowledge & Retrieval dashboard
Metrics:
- Knowledge Coverage
- Retrieval Recall
- Retrieval Precision
- Context Utilization
- Knowledge Conflict Rate

### Knowledge Gap Map
Rows by topic:
- topic
- question volume
- affected calls
- coverage
- trend
- languages

Topic detail:
- representative original questions
- current source/chunk coverage
- missing concepts
- safe recommendation
- explicit “business verification required” if facts are unknown.

## 10. Tools dashboard
KPI cards:
- Tool Selection Accuracy
- Tool Timing Accuracy
- Argument Accuracy
- Result Utilization
- Complete Trajectory Success

Tool funnel:
Tool needed -> correct selected -> correct args -> execution success -> correct result use.

Failure breakdown:
- required tool not called
- wrong tool
- too early/late
- wrong/missing/fabricated args
- result ignored/misinterpreted

Each tool has a detail page.

## 11. Recommendations workspace
Tabs:
- Needs review
- Approved
- Rejected
- Applied/Exported
- Monitoring

Recommendation card:
- confidence
- severity
- finding title
- root cause
- affected calls
- language distribution
- change type
- expected impact
- regression summary

## 12. Recommendation review
Three-pane preferred desktop layout:
- Evidence
- Proposed Change
- Validation/Regression

Actions:
- Approve as draft/export
- Edit proposal
- Reject
- Mark not an issue
- Request review

Never present an “Apply to production” action in V1.

## 13. Regression comparison
Table baseline vs candidate:
- overall pass
- critical failure rate
- grounding
- tool accuracy
- KB/RAG metrics where applicable
- conversation quality

Show:
- fixed cases
- unchanged failures
- new regressions
- critical regressions

All newly failing cases are inspectable.

## 14. Eval Setup
### Rubrics
Create/edit versioned rubric with:
- name
- description
- scope
- severity
- applicability
- PASS guidance
- FAIL guidance
- exceptions
- evidence required

### Eval Suites
Select evaluator definitions/rubrics; configure thresholds.

### Routing profile
Simple mode: one provider/model for all.
Advanced: per evaluator family model/provider.
Optional verification/consensus/fallback settings.

## 15. Integrations page
Show each source/provider connection and status.
For data integrations show:
- Level 1/2/3 integration maturity
- last ingestion
- records imported
- fields missing
- what additional evals would unlock

## 16. AI Providers settings
Cards:
- provider
- connection state
- default model
- last test
- usage/request success

Credential values never redisplayed.

## 17. Cost and provider health
Metrics:
- evaluator requests
- request success
- P95 latency
- input/output tokens
- estimated cost
- cost per evaluated conversation

## 18. States
Every main view must have:
- useful empty state
- loading/skeleton state
- recoverable error state
- partial-data warning state
- insufficient sample warning

## 19. Accessibility/responsiveness
- Keyboard navigable
- WCAG-conscious contrast
- meaningful chart labels/tooltips
- tables usable on laptop widths
- responsive mobile read-only experience acceptable, but desktop is primary for V1.
