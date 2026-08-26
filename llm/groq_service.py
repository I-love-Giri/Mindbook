import json
import logging
from typing import TypeVar

from groq import (
    APIConnectionError,
    APITimeoutError,
    AsyncGroq,
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

from config.settings import GROQ_API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_SYSTEM_PROMPT = "You are an expert assistant for analyzing YouTube transcripts."


class LLMService:

    def __init__(self):
        self.client = AsyncGroq(
            api_key=GROQ_API_KEY,
            timeout=30.0,
        )

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
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        response_schema: type[T] | None = None,
        json_output: bool = False,
    ) -> str | dict | T:

        request_kwargs = {
            "model": MODEL_NAME,
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
            "max_completion_tokens": max_tokens,
        }

        if response_schema:
            request_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "strict": True,
                    "schema": response_schema.model_json_schema(),
                },
            }

        elif json_output:
            request_kwargs["response_format"] = {
                "type": "json_object",
            }

        response = await self.client.chat.completions.create(
            **request_kwargs,
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("LLM returned an empty response.")

        if response_schema:
            return response_schema.model_validate_json(content)

        if json_output:
            return json.loads(content)

        return content.strip()


"""

llm = LLMService()

answer = llm.generate(
    "Explain Python in one paragraph."
)

print(answer)

Output: 

Python is a high‑level, interpreted programming language known for its clean, readable syntax and strong emphasis on code readability, which makes it an excellent choice for both beginners and experienced developers. It supports multiple programming paradigms—including procedural, object‑oriented, and functional styles—and comes with a massive standard library plus a vibrant ecosystem of third‑party packages for tasks ranging from web development and data analysis to machine learning and automation. Python’s dynamic typing, automatic memory management, and interactive interpreter enable rapid development and prototyping, while its cross‑platform nature ensures code can run on Windows, macOS, Linux, and many other systems with little or no modification.

"""
"""
Retries Logic :

Option 1: For a Groq-only project, though, the SDK's built-in retry support is the simpler and more idiomatic choice.

Option 2: Simple manual retries (good for small projects)

Option 3: tenacity: If your application makes several API calls, this is the standard Python solution.

Option 4: Put retries inside LLMService 
If you eventually support multiple providers (Groq, OpenAI, Anthropic, Gemini, etc.), then using tenacity in your own LLMService can make sense because you'd have one consistent retry policy regardless of the underlying SDK.

other options : 

| Exponential backoff with jitter |
Instead of every client retrying after exactly 2 seconds:

1.3s
2.8s
4.6s

Random "jitter" reduces the chance of many clients retrying simultaneously.

| Circuit breaker (for larger systems) |

If the provider is clearly down, stop retrying for a short period instead of repeatedly sending requests.

"""


"""
Ek generic LLMService banaya
Har use-case ke liye alag function nahi banana.
Ek hi generate() function se different LLM calls handle hongi.

Normal text generation support

result = await llm_service.generate(
    prompt=prompt
)

→ simple str response.

JSON output support

result = await llm_service.generate(
    prompt=prompt,
    json_output=True
)

→ valid JSON ko Python dict mein convert karna.

Structured output / enforced schema support

result = await llm_service.generate(
    prompt=prompt,
    response_schema=ContentParserResult
)

→ LLM ko expected structure enforce karna using Pydantic schema.

Schema ko globally enforce nahi kiya
response_schema optional rakha.
Jahan schema chahiye → pass karo.
Jahan simple answer chahiye → kuch pass mat karo.
Isse future mein dozens of different LLM calls easily handle hongi.
Async support rakha
Groq ke liye AsyncGroq
await llm_service.generate(...)
Backend/API applications ke liye better fit.
Retry + exponential backoff add kiya
Connection error
Timeout
Rate limit
Temporary failures par automatically retry.
Basically architecture ye ban gaya:
                    LLMService
                        │
                    generate()
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
       Text           JSON        Pydantic
       output         output       Schema
          │             │             │
         str           dict      BaseModel


"""
