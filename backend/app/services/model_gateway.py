from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib import error, request

from app.services.prompt_builder import PromptBundle
from app.services.runtime_model import RuntimeModelConfig


BASE_DIR = Path(__file__).resolve().parents[2]
NEXT_STEP_SCHEMA_PATH = BASE_DIR.parent / "shared" / "contracts" / "next-step-response.schema.json"
NEXT_STEP_SCHEMA_VERSION = "next-step-response.v1"


class ModelGatewayError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        raw_response_excerpt: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.raw_response_excerpt = raw_response_excerpt


class ModelGateway:
    def generate_next_step(
        self,
        runtime_model_config: RuntimeModelConfig,
        prompt_bundle: PromptBundle,
    ) -> dict[str, Any]:
        raise NotImplementedError


class OpenAIResponsesGateway(ModelGateway):
    def __init__(self) -> None:
        self._response_schema = self._load_next_step_schema()

    @property
    def response_schema_version(self) -> str:
        return NEXT_STEP_SCHEMA_VERSION

    def generate_next_step(
        self,
        runtime_model_config: RuntimeModelConfig,
        prompt_bundle: PromptBundle,
    ) -> dict[str, Any]:
        if not runtime_model_config.has_model_access:
            raise ModelGatewayError(
                "model access not configured",
                code="model_access_not_configured",
            )

        api_mode = self._detect_api_mode(
            base_url=runtime_model_config.base_url,
            provider=runtime_model_config.provider,
        )
        use_responses_api = api_mode == "responses"
        request_url = self._resolve_request_url(
            base_url=runtime_model_config.base_url,
            api_mode=api_mode,
        )
        payload = self._build_request_payload(
            prompt_bundle=prompt_bundle,
            model_type=runtime_model_config.model_type,
            use_responses_api=use_responses_api,
        )

        request_body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            request_url,
            data=request_body,
            headers={
                "Authorization": f"Bearer {runtime_model_config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=runtime_model_config.request_timeout_seconds) as response:
                raw_payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise ModelGatewayError(
                f"model request failed with HTTP {exc.code}: {details}",
                code="http_error",
                raw_response_excerpt=self._build_excerpt(details),
            ) from exc
        except error.URLError as exc:
            raise ModelGatewayError(
                f"model request failed: {exc.reason}",
                code="network_error",
            ) from exc

        try:
            parsed_payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ModelGatewayError(
                "model returned invalid JSON envelope",
                code="invalid_json_envelope",
                raw_response_excerpt=self._build_excerpt(raw_payload),
            ) from exc

        json_text = self._extract_output_text(parsed_payload, use_responses_api=use_responses_api)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ModelGatewayError(
                "model returned invalid JSON response body",
                code="invalid_json_body",
                raw_response_excerpt=self._build_excerpt(json_text),
            ) from exc

    @staticmethod
    def _load_next_step_schema() -> dict[str, Any]:
        return json.loads(NEXT_STEP_SCHEMA_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _extract_output_text(payload: dict[str, Any], *, use_responses_api: bool) -> str:
        if not use_responses_api:
            return OpenAIResponsesGateway._extract_chat_completions_text(payload)

        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        output_items = payload.get("output")
        if isinstance(output_items, list):
            for item in output_items:
                if not isinstance(item, dict):
                    continue
                content_items = item.get("content")
                if not isinstance(content_items, list):
                    continue
                for content_item in content_items:
                    if not isinstance(content_item, dict):
                        continue
                    text_value = content_item.get("text")
                    if isinstance(text_value, str) and text_value.strip():
                        return text_value

        raise ModelGatewayError(
            "model response did not include output text",
            code="missing_output_text",
            raw_response_excerpt=OpenAIResponsesGateway._build_excerpt(json.dumps(payload, ensure_ascii=False)),
        )

    @staticmethod
    def _extract_chat_completions_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelGatewayError(
                "model response did not include choices",
                code="missing_output_text",
                raw_response_excerpt=OpenAIResponsesGateway._build_excerpt(json.dumps(payload, ensure_ascii=False)),
            )

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ModelGatewayError(
                "model response choice is invalid",
                code="missing_output_text",
                raw_response_excerpt=OpenAIResponsesGateway._build_excerpt(json.dumps(payload, ensure_ascii=False)),
            )

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise ModelGatewayError(
                "model response did not include message",
                code="missing_output_text",
                raw_response_excerpt=OpenAIResponsesGateway._build_excerpt(json.dumps(payload, ensure_ascii=False)),
            )

        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    return text

        raise ModelGatewayError(
            "model response did not include message content",
            code="missing_output_text",
            raw_response_excerpt=OpenAIResponsesGateway._build_excerpt(json.dumps(payload, ensure_ascii=False)),
        )

    @staticmethod
    def _build_excerpt(raw_text: str, limit: int = 500) -> str:
        compact_text = " ".join(raw_text.split())
        if len(compact_text) <= limit:
            return compact_text
        return f"{compact_text[:limit]}..."
    @staticmethod
    def _detect_api_mode(*, base_url: str, provider: str) -> str:
        normalized = base_url.strip().lower().rstrip("/")
        if normalized.endswith("/responses"):
            return "responses"
        if normalized.endswith("/chat/completions"):
            return "chat_completions"

        # Keep OpenAI official default on Responses API; compatible providers default to chat-completions.
        if provider.strip().lower() == "openai":
            return "responses"
        return "chat_completions"

    @staticmethod
    def _resolve_request_url(*, base_url: str, api_mode: str) -> str:
        normalized = base_url.strip().rstrip("/")
        if not normalized:
            return normalized

        if api_mode == "responses":
            if normalized.lower().endswith("/responses"):
                return normalized
            return f"{normalized}/responses"

        if normalized.lower().endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"

    def _build_request_payload(
        self,
        *,
        prompt_bundle: PromptBundle,
        model_type: str,
        use_responses_api: bool,
    ) -> dict[str, Any]:
        if use_responses_api:
            return {
                "model": model_type,
                "input": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": prompt_bundle.system_prompt,
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": prompt_bundle.user_prompt,
                            }
                        ],
                    },
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "next_step_response",
                        "strict": True,
                        "schema": self._response_schema,
                    }
                },
            }

        return {
            "model": model_type,
            "messages": [
                {"role": "system", "content": prompt_bundle.system_prompt},
                {"role": "user", "content": prompt_bundle.user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
