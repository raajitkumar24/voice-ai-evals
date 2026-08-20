# README Blueprint for the Final Repository

Codex should turn this blueprint into the repository README.

## Hero
**Voice AI Evals**
Open-source evaluation and observability for production Voice AI agents.

One-liner:
Ingest conversations, prompts, RAG traces and tool calls; evaluate multilingual agent behavior with your choice of LLM provider; diagnose root causes; and generate human-reviewed improvement recommendations.

Badges:
- CI
- License
- Python/Node versions as appropriate
- Docker

## Why
Voice-agent failures can originate in prompts, missing knowledge, retrieval, tool selection/timing/arguments, model behavior, or conversation design. A single quality score is not enough. Voice AI Evals traces failures to the owning layer and links every recommendation to evidence.

## Key features
- LLM-provider agnostic
- Voice-platform agnostic
- Multilingual + code-switching
- Rubric/response evals
- Hallucination/grounding
- RAG/knowledge diagnostics
- Tool trajectory evals
- Conversation quality
- Root-cause analysis
- Human-reviewed prompt/KB/tool recommendations
- Regression testing
- UI + REST API + CLI
- Self-hostable Docker deployment
- BYOK/local model support

## Safety promise
**Voice AI Evals never changes your production agent automatically.**
Recommendations require human review and are exported/created as draft artifacts only.

## Quickstart
Expected experience:

```bash
git clone <repo>
cd voice-ai-evals
cp .env.example .env
docker compose up -d --build
make demo
```

Open local web URL.

## Provider setup
Explain OpenAI, Anthropic, Gemini, OpenAI-compatible, Ollama.
Do not include real keys.

## Data ingestion
- Sample dataset
- Upload
- REST
- Webhook
- SDK

Link canonical schema docs.

## Architecture
Small diagram and links to docs.

## Demo
Explain seeded multilingual failures.

## CLI examples
Import, run, findings, CI threshold.

## Testing
`make test-all`
Optional live provider tests separately.

## Contributing
Provider/connector/evaluator extension points.

## Security
Link SECURITY.md.

## License
Apache-2.0 recommended.
