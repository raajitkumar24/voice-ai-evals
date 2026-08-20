from __future__ import annotations

import os

from voice_evals_llm_gateway import LLMProvider
from voice_evals_llm_providers import build_provider

from ..config import Settings
from ..models import ProviderConnection
from ..security import SecretCipher


def environment_secret(provider: str) -> str | None:
    variable = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openai-compatible": "OPENAI_COMPATIBLE_API_KEY",
    }.get(provider)
    return os.environ.get(variable) if variable else None


def provider_for_record(record: ProviderConnection, settings: Settings) -> LLMProvider:
    secret: str | None = None
    if record.secret_source == "ENCRYPTED_DB" and record.secret_ciphertext:
        secret = SecretCipher(settings.encryption_key).decrypt(record.secret_ciphertext)
    elif record.secret_source == "ENVIRONMENT":
        secret = environment_secret(record.provider)
    return build_provider(
        record.provider,
        api_key=secret,
        base_url=record.base_url,
        capability_overrides=record.capability_overrides,
        enable_test_provider=settings.enable_test_provider,
    )
