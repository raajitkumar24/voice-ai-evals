# Master Codex Build Instructions — Voice AI Evals

## Objective
Build the complete open-source **Voice AI Evals** product described in this build pack as a production-quality, self-hostable GitHub repository.

The finished repository must allow a developer to:
1. clone the repo;
2. configure one or more LLM providers using environment variables or the UI;
3. start the product with Docker Compose;
4. import a sample multilingual voice-agent dataset or ingest traces through an API;
5. configure eval rubrics/suites;
6. run evaluations asynchronously;
7. view quality/risk dashboards;
8. inspect findings down to conversation-turn evidence;
9. review hallucination/RAG/tool/conversation failures;
10. receive root-cause and improvement recommendations;
11. regression-test candidate prompt/KB/tool patches;
12. approve/edit/reject recommendations without automatically changing production agents;
13. use the CLI/API without the UI;
14. run the full automated test suite.

## Source of truth
Read all files in this build pack before implementation. Priority order:
1. `AGENTS.md`
2. `01_PRODUCT_SPEC.md`
3. `02_SYSTEM_ARCHITECTURE.md`
4. `03_DATA_CONTRACTS.md`
5. `04_EVALUATION_FRAMEWORK.md`
6. `05_UX_UI_SPEC.md`
7. `06_INTEGRATIONS_AND_LLM_PROVIDERS.md`
8. `07_SECURITY_AND_OPERATIONS.md`
9. `08_IMPLEMENTATION_PLAN.md`
10. `09_TEST_STRATEGY.md`
11. `10_E2E_TEST_CASES.md`

When ambiguity remains, choose the option that best preserves provider agnosticism, reproducibility, human control, testability, and simplicity.

## Execution rules for Codex
- Do not stop at scaffolding. Build functional vertical slices.
- Do not replace functional requirements with TODO comments.
- Do not create fake integrations that always succeed. Provider adapters may be mocked in tests but production adapters must make real provider API calls when credentials are supplied.
- Do not require any single LLM vendor.
- Do not make external production-agent writebacks in V1.
- Do not invent business facts when generating KB recommendations; distinguish “knowledge missing” from “suggested verified content.”
- Keep evaluator prompts versioned in files, not embedded in application logic.
- Use structured outputs validated against schemas.
- Maintain deterministic IDs/versioning for eval definitions.
- Every DB schema change requires migration.
- Use feature flags only when necessary; do not hide unfinished core scope behind flags.

## Build sequence
Implement in the phases in `08_IMPLEMENTATION_PLAN.md`. After each phase:
1. run the phase acceptance tests;
2. fix failures before proceeding;
3. update `BUILD_STATUS.md` with completed scope, test results, known limitations, and next phase.

## Required final repository artifacts
At minimum:
- `README.md`
- `LICENSE` (Apache-2.0 recommended unless project owner chooses another)
- `CONTRIBUTING.md`
- `SECURITY.md`
- `AGENTS.md`
- `.env.example`
- `docker-compose.yml`
- `Makefile`
- database migrations
- sample/demo data
- OpenAPI docs
- API examples
- CLI
- evaluator definitions
- provider adapters
- connector SDK/contract
- automated tests
- GitHub Actions CI

## Final verification
Before declaring complete, run:

```bash
make test-all
make demo
```

Then perform the E2E scenarios in `10_E2E_TEST_CASES.md`, including multilingual and provider-switching scenarios.

Create `FINAL_VERIFICATION.md` containing:
- commit SHA tested;
- environment used;
- commands executed;
- unit/integration/E2E results;
- demo result;
- supported providers tested live vs mocked;
- screenshots/links if the environment supports them;
- known limitations;
- any requirements not completed.

Do not claim completion if mandatory tests fail.
