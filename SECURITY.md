# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub Security Advisories for this repository. Do not include credentials, real transcripts, or customer data in a report.

## Security boundaries

- Provider credentials remain backend-only and encrypted at rest when stored.
- External integrations are read-only in V1.
- Recommendation approval never publishes production configuration.
- Every data query is scoped to a workspace.
- Transcripts and knowledge content are untrusted evaluator evidence, not instructions.

Until the first stable release, security fixes are applied to the latest `main` branch.
