import asyncio
import json
import logging
from enum import Enum
from typing import Any, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from pydantic import BaseModel

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from config.settings import (
    OPENROUTER_API_KEY,
    OPENROUTER_SITE_URL,
    OPENROUTER_APP_NAME,
    OPENROUTER_TEXT_MODELS,
    OPENROUTER_FAST_MODELS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


DEFAULT_SYSTEM_PROMPT = "You are an expert assistant for analyzing YouTube transcripts."


# ============================================================
# MODEL TYPE
# ============================================================


class ModelType(str, Enum):
    TEXT = "text"
    FAST = "fast"


# ============================================================
# LLM SERVICE
# ============================================================


class OpenrouterService:

    _request_lock = asyncio.Lock()
    _next_request_at = 0.0
    _minimum_request_gap_seconds = 1.2

    def __init__(self):

        self.client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            timeout=30.0,
            default_headers={
                "HTTP-Referer": OPENROUTER_SITE_URL,
                "X-Title": OPENROUTER_APP_NAME,
            },
        )

    # ========================================================
    # MODEL SELECTION
    # ========================================================

    @staticmethod
    def _get_models(
        model_type: ModelType,
    ) -> list[str]:

        if model_type == ModelType.FAST:
            return OPENROUTER_FAST_MODELS

        return OPENROUTER_TEXT_MODELS

    # ========================================================
    # GENERATE
    # ========================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(
            multiplier=1,
            max=10,
        ),
        retry=retry_if_exception_type(
            (
                APIConnectionError,
                APITimeoutError,
                RateLimitError,
            )
        ),
        before_sleep=before_sleep_log(
            logger,
            logging.WARNING,
        ),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        model_type: ModelType = ModelType.FAST,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        response_schema: type[T] | None = None,
        json_output: bool = False,
    ) -> str | dict[str, Any] | T:

        # ----------------------------------------------------
        # Get model list
        # ----------------------------------------------------

        models = self._get_models(model_type)

        if not models:

            raise ValueError(
                f"No OpenRouter models configured " f"for model type: {model_type}"
            )

        # ----------------------------------------------------
        # Primary model
        # ----------------------------------------------------

        primary_model = models[0]

        # ----------------------------------------------------
        # Request
        # ----------------------------------------------------

        request_kwargs = {
            "model": primary_model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # ----------------------------------------------------
        # OpenRouter fallback models
        # ----------------------------------------------------

        fallback_models = models[1:]

        if fallback_models:

            request_kwargs["extra_body"] = {
                "models": fallback_models,
            }

        # ----------------------------------------------------
        # Structured JSON
        # ----------------------------------------------------

        if response_schema:

            request_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "strict": True,
                    "schema": (response_schema.model_json_schema()),
                },
            }

        # ----------------------------------------------------
        # Simple JSON
        # ----------------------------------------------------

        elif json_output:

            request_kwargs["response_format"] = {
                "type": "json_object",
            }

        # ----------------------------------------------------
        # Logging
        # ----------------------------------------------------

        logger.info(
            "OpenRouter request | " "model=%s | " "type=%s | " "fallbacks=%d",
            primary_model,
            model_type.value,
            len(fallback_models),
        )

        # ----------------------------------------------------
        # API CALL
        # ----------------------------------------------------

        async with self._request_lock:
            loop = asyncio.get_running_loop()
            wait_for = self._next_request_at - loop.time()
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._next_request_at = loop.time() + self._minimum_request_gap_seconds
            try:
                response = await self.client.chat.completions.create(
                    **request_kwargs,
                )
            except RateLimitError as exc:
                # Respect a provider cooldown when it is supplied. The retry
                # decorator then retries only after this shared gate opens.
                retry_after = 0.0
                headers = getattr(getattr(exc, "response", None), "headers", {})
                try:
                    retry_after = float(headers.get("retry-after", 0))
                except (TypeError, ValueError):
                    retry_after = 0.0
                self._next_request_at = max(
                    self._next_request_at,
                    loop.time() + max(retry_after, self._minimum_request_gap_seconds),
                )
                raise

        # ----------------------------------------------------
        # Extract response
        # ----------------------------------------------------

        if not response.choices:

            raise ValueError("OpenRouter returned no choices.")

        content = response.choices[0].message.content

        if not content:

            raise ValueError("OpenRouter returned an empty response.")

        # ----------------------------------------------------
        # Pydantic response
        # ----------------------------------------------------

        if response_schema:

            return response_schema.model_validate_json(content)

        # ----------------------------------------------------
        # JSON response
        # ----------------------------------------------------

        if json_output:

            return json.loads(content)

        # ----------------------------------------------------
        # Normal text
        # ----------------------------------------------------

        return content.strip()

    # ========================================================
    # CLOSE
    # ========================================================

    async def close(self):

        await self.client.close()
