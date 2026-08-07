from abc import ABC, abstractmethod
import json


class BaseLLMService(ABC):
    SYSTEM_PROMPT = (
        "You are an expert assistant "
        "for summarizing YouTube transcripts."
    )

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        json_output: bool = False,
    ):
        content = self._generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_output=json_output,
        )

        if json_output:
            return json.loads(content)

        return content

    @abstractmethod
    def _generate(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        json_output: bool,
    ) -> str:
        """Return raw text from the provider."""
