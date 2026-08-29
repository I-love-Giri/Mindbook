"""import logging
from typing import TypeVar

from google import genai
from pydantic import BaseModel
from google.genai import types
from google.genai.errors import APIError

T = TypeVar("T", bound=BaseModel)

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from config.settings import GEMINI_API_KEY, GEMINI_MODEL_NAME

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(APIError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        response_schema: type[T] | None = None,
    ) -> str | T:

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=(
                "You are an expert assistant " "for analyzing YouTube transcripts."
            ),
        )

        if response_schema:
            config.response_mime_type = "application/json"
            config.response_schema = response_schema

        response = self.client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=config,
        )

        if response_schema:
            return response.parsed

        return response.text"""

"""import json
import logging
from typing import TypeVar

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from config.settings import GEMINI_API_KEY, GEMINI_MODEL_NAME

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_SYSTEM_PROMPT = "You are an expert assistant for analyzing YouTube transcripts."


class GeminiService:

    def __init__(self):
        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(
            multiplier=1,
            max=10,
        ),
        retry=retry_if_exception_type(APIError),
        before_sleep=before_sleep_log(
            logger,
            logging.WARNING,
        ),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        response_schema: type[T] | None = None,
        json_output: bool = False,
    ) -> str | dict | T:

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )

        # Structured JSON using Pydantic schema
        if response_schema:
            config.response_mime_type = "application/json"
            config.response_schema = response_schema

        # Generic JSON output
        elif json_output:
            config.response_mime_type = "application/json"

        response = await self.client.aio.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=config,
        )

        print("FINISH REASON:", response.candidates[0].finish_reason)
        print("USAGE:", response.usage_metadata)

        if response_schema:
            return response.parsed

        if json_output:
            content = response.text

            if not content:
                raise ValueError("LLM returned an empty response.")

            print("GEMINI RAW RESPONSE:")
            print(repr(content))
            print("END GEMINI RESPONSE")

            return json.loads(content)

        if not response.text:
            raise ValueError("LLM returned an empty response.")

        return response.text.strip()"""


import json
import logging
from typing import TypeVar

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from config.settings import GEMINI_API_KEY, GEMINI_MODEL_NAME

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_SYSTEM_PROMPT = "You are an expert assistant for analyzing YouTube transcripts."


class GeminiService:

    def __init__(self):
        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(
            multiplier=1,
            max=10,
        ),
        retry=retry_if_exception_type(APIError),
        before_sleep=before_sleep_log(
            logger,
            logging.WARNING,
        ),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        response_schema: type[T] | None = None,
        json_output: bool = False,
    ) -> str | dict | T:

        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "system_instruction": system_prompt,
        }

        if response_schema:
            config_kwargs.update(
                {
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                }
            )

        elif json_output:
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs)

        response = await self.client.aio.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=config,
        )

        if not response.candidates:
            raise ValueError("Gemini returned no candidates.")

        candidate = response.candidates[0]
        usage = response.usage_metadata

        logger.info(
            "Gemini finish reason: %s",
            candidate.finish_reason,
        )

        logger.info(
            "Gemini tokens | input=%s | output=%s | total=%s",
            usage.prompt_token_count,
            usage.candidates_token_count,
            usage.total_token_count,
        )

        # Pydantic structured response
        if response_schema:
            parsed = response.parsed

            if parsed is None:
                raise ValueError("Gemini returned no parsed structured response.")

            return parsed

        # Generic JSON response
        if json_output:
            content = response.text

            if not content:
                raise ValueError("Gemini returned an empty response.")

            try:
                return json.loads(content)
            except json.JSONDecodeError as exc:
                logger.error(
                    "Failed to decode Gemini JSON response: %r",
                    content,
                )
                raise ValueError("Gemini returned invalid JSON.") from exc

        # Plain text response
        content = response.text

        if not content:
            raise ValueError("Gemini returned an empty response.")

        return content.strip()
