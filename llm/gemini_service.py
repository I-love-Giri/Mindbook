import json
import logging

from google import genai
from google.genai import types
from google.genai.errors import APIError

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
        json_output: bool = False,
    ):
        """
        Generate text from Gemini.

        Args:
            prompt: User prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            json_output: Whether to request JSON output.

        Returns:
            str | dict
        """

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=(
                "You are an expert assistant "
                "for summarizing YouTube transcripts."
            ),
        )

        if json_output:
            config.response_mime_type = "application/json"

        response = self.client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=config,
        )

        content = response.text

        if json_output:
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON response: %s", e)
                raise

        return content
