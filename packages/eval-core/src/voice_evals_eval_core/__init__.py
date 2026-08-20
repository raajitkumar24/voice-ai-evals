"""Provider-neutral evaluation orchestration and domain logic."""

from .definitions import load_eval_definitions
from .evaluator import SpecialistEvaluator, specialist_evaluators
from .models import (
    EvalDefinition,
    EvaluationContext,
    JudgeOutput,
    RecommendationOutput,
    RootCauseOutput,
)
from .synthesis import generate_recommendation, synthesize_root_cause

__all__ = [
    "EvalDefinition",
    "EvaluationContext",
    "JudgeOutput",
    "RecommendationOutput",
    "RootCauseOutput",
    "SpecialistEvaluator",
    "load_eval_definitions",
    "specialist_evaluators",
    "generate_recommendation",
    "synthesize_root_cause",
]
