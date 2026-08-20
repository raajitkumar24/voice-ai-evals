# Contributing

Thank you for helping build Voice AI Evals.

1. Read `AGENTS.md` and the relevant numbered specifications.
2. Keep provider SDK concerns inside `packages/llm-providers`.
3. Normalize external voice-platform data before it reaches evaluation core.
4. Add or update tests with each behavior change.
5. Run `make lint`, `make typecheck`, and the affected test suites.
6. Never commit credentials, real customer transcripts, or production PII.

Pull requests should describe the behavior changed, tests run, schema/migration impact, and any provider-specific behavior.
