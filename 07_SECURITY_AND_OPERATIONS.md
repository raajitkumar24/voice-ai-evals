# Security and Operations Specification

## 1. Secrets
- Secrets are backend-only.
- Never place provider credentials in browser localStorage/sessionStorage/indexedDB.
- `.env` is gitignored; `.env.example` contains placeholders only.
- Encrypted DB mode uses authenticated encryption and a deployment-level encryption key.
- Mask secrets in UI after save.
- Redact likely secrets in logs/errors.

## 2. External data privacy
Call transcripts may contain PII.
- Do not emit full transcripts to application logs by default.
- UI access must be workspace/auth scoped.
- Offer configurable transcript retention later; schema should support soft deletion/retention metadata.
- Make outbound LLM use explicit in provider setup/help text.
- Local-model support enables fully private deployments.

## 3. Authentication
V1 acceptable baseline:
- local user auth for UI;
- workspace-scoped API keys for ingestion/SDK.

Hash API keys at rest where possible; display only once at creation.

## 4. Authorization
Enforce workspace ownership on every entity/query.
Add tests preventing cross-workspace access.

## 5. Upload safety
- MIME/type validation
- extension validation
- size limits
- path traversal protection
- safe filenames
- no direct execution
- parse documents in constrained service/process where feasible

## 6. Prompt-injection awareness
Customer transcripts and KB content are untrusted data to evaluator judges.
Evaluator prompts must explicitly treat them as evidence, not instructions.
Use clear delimiters/typed structured inputs.
Do not allow transcript text to override evaluator system instructions.

## 7. Provider request minimization
Send only the data required by an evaluator. Avoid sending unrelated transcripts, credentials, internal config, or other workspace data.

## 8. Auditability
Audit events:
- provider connection created/tested/updated/deleted
- ingestion API key created/revoked
- eval run created/cancelled
- recommendation reviewed
- recommendation edited/approved/rejected
- exports

## 9. Operational health
Expose health endpoints:
- API
- DB
- Redis/queue
- worker

Provider connection health is workspace-specific and should not be part of global liveness checks.

## 10. Retry/idempotency
- webhook ingestion idempotent
- batch imports resumable where practical
- eval tasks safe to retry
- provider calls have bounded retry policy

## 11. Cost controls
Workspace settings:
- max calls per eval run
- sampling percentage
- optional estimated budget ceiling
- optional daily evaluator request ceiling

Warn before expensive runs when estimate available.

## 12. Dependency/security hygiene
- pin/lock dependencies
- automated dependency update workflow optional
- CI vulnerability scan recommended
- secret scanning recommended
- no credentials/sample real PII in fixtures

## 13. Human approval safety invariant
No backend endpoint in V1 may directly publish/update external production agent configuration.
Tests must assert no connector write method exists in the V1 public connector contract.
