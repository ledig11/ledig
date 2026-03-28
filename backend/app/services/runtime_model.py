from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RuntimeModelConfig:
    provider: str
    model_type: str
    api_key: Optional[str]
    base_url: str
    request_timeout_seconds: float

    @property
    def has_model_access(self) -> bool:
        return bool(self.model_type.strip()) and bool((self.api_key or "").strip())


def resolve_runtime_model_config(
    provider_header: Optional[str],
    model_type_header: Optional[str],
    api_key_header: Optional[str],
    base_url_header: Optional[str],
) -> RuntimeModelConfig:
    provider = (
        (provider_header or "").strip()
        or os.getenv("WINDOWS_STEP_GUIDE_MODEL_PROVIDER", "").strip()
        or "openai"
    )
    model_type = (
        (model_type_header or "").strip()
        or os.getenv("WINDOWS_STEP_GUIDE_MODEL_TYPE", "").strip()
        or "gpt-4.1"
    )
    api_key = (
        (api_key_header or "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
        or None
    )
    base_url = (
        (base_url_header or "").strip()
        or
        os.getenv("WINDOWS_STEP_GUIDE_MODEL_BASE_URL", "").strip()
        or "https://api.openai.com/v1/responses"
    )

    timeout_raw = os.getenv("WINDOWS_STEP_GUIDE_MODEL_TIMEOUT_SECONDS", "20").strip()
    try:
        request_timeout_seconds = max(float(timeout_raw), 1.0)
    except ValueError:
        request_timeout_seconds = 20.0

    return RuntimeModelConfig(
        provider=provider,
        model_type=model_type,
        api_key=api_key,
        base_url=base_url,
        request_timeout_seconds=request_timeout_seconds,
    )
