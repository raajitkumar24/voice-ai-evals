from __future__ import annotations

from pathlib import Path

import yaml

from .models import EvalDefinition


def default_evals_directory() -> Path:
    candidates = [Path.cwd() / "evals", Path(__file__).resolve().parents[4] / "evals"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate the versioned evaluator definitions directory")


def load_eval_definitions(directory: Path | None = None) -> list[EvalDefinition]:
    root = directory or default_evals_directory()
    definitions: list[EvalDefinition] = []
    for path in sorted(root.glob("*/definition.yaml")):
        with path.open(encoding="utf-8") as source:
            payload = yaml.safe_load(source)
        if not isinstance(payload, dict):
            raise ValueError(f"Evaluator definition must be an object: {path}")
        prompt_file = path.parent / str(payload.pop("prompt_file"))
        payload["prompt_template"] = prompt_file.read_text(encoding="utf-8")
        definitions.append(EvalDefinition.model_validate(payload))
    if not definitions:
        raise ValueError(f"No evaluator definitions found beneath {root}")
    identities = [(definition.id, definition.version) for definition in definitions]
    if len(identities) != len(set(identities)):
        raise ValueError("Evaluator IDs and versions must be unique")
    return definitions
