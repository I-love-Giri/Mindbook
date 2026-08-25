import logging
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


class GeminiService:
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

        return response.text
