from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import typer
from voice_evals_schemas import ConversationTrace

from .client import VoiceEvalsClient, VoiceEvalsError

app = typer.Typer(help="Import traces, run evaluations, and inspect findings.")


def _client(base_url: str, api_key: str | None) -> VoiceEvalsClient:
    return VoiceEvalsClient(base_url, api_key or os.getenv("VOICE_EVALS_API_KEY"))


def _traces(path: Path) -> list[ConversationTrace]:
    if not path.is_file():
        raise typer.BadParameter(f"File does not exist: {path}")
    try:
        if path.suffix.lower() == ".jsonl":
            payloads = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        elif path.suffix.lower() == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
            payloads = value if isinstance(value, list) else [value]
        else:
            raise typer.BadParameter("Only canonical .json and .jsonl files are supported")
        return [ConversationTrace.model_validate(item) for item in payloads]
    except (json.JSONDecodeError, ValueError) as exc:
        raise typer.BadParameter(f"Invalid canonical trace file: {exc}") from exc


@app.command("init")
def initialize() -> None:
    """Print the local quickstart without writing secrets."""
    typer.echo(
        "Copy .env.example to .env, configure credentials, then run: docker compose up --build"
    )


@app.command("import-file")
def import_file(
    path: Path,
    base_url: str = typer.Option("http://localhost:8000", envvar="VOICE_EVALS_API_URL"),
    api_key: str | None = typer.Option(None, envvar="VOICE_EVALS_API_KEY", hide_input=True),
) -> None:
    """Validate and import canonical JSON or JSONL traces."""
    traces = _traces(path)
    try:
        with _client(base_url, api_key) as client:
            result = client.ingest_batch(traces)
    except VoiceEvalsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Accepted {result['accepted']}; rejected {result['rejected']} trace(s).")


@app.command("demo-load")
def demo_load(
    directory: Path = Path("examples/loan-agent-demo"),
    base_url: str = typer.Option("http://localhost:8000", envvar="VOICE_EVALS_API_URL"),
    email: str = typer.Option("admin@example.com", envvar="VOICE_EVALS_BOOTSTRAP_EMAIL"),
    password: str = typer.Option(
        "change-me-before-production", envvar="VOICE_EVALS_BOOTSTRAP_PASSWORD", hide_input=True
    ),
) -> None:
    """Load the intentionally failing multilingual local demo."""
    manifest_path = directory / "manifest.json"
    traces_path = directory / "conversations.jsonl"
    if not manifest_path.is_file():
        raise typer.BadParameter(f"Demo manifest does not exist: {manifest_path}")
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    traces = _traces(traces_path)
    try:
        with VoiceEvalsClient(base_url) as client:
            client.login(email, password)
            agent = manifest["agent"]
            client.upsert_agent(agent["external_id"], agent["name"], agent.get("description"))
            for source in manifest.get("knowledge_sources", []):
                client.upsert_knowledge_source(source)
            for definition in manifest.get("tool_definitions", []):
                client.upsert_tool_definition(definition)
            client.upsert_agent_configuration(agent["external_id"], manifest["configuration"])
            result = client.ingest_batch(traces)
    except VoiceEvalsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"Demo ready: accepted {result['accepted']} multilingual trace(s). "
        "Connect a judge provider in the UI, then run the default suite."
    )


if __name__ == "__main__":
    app()
