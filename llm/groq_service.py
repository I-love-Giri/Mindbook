import json
import logging
import re

from groq import (
    APIConnectionError,
    APITimeoutError,
    AsyncGroq,
    RateLimitError,
)

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from config.settings import GROQ_API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = "You are an expert assistant for analyzing YouTube transcripts."

JSON_INSTRUCTION = (
    "Respond only with valid json. " "Do not include markdown or commentary."
)


def _extract_json(text: str):
    """
    Best-effort JSON extraction from an LLM response.

    Attempts:
    1. Direct json.loads()
    2. Extract first complete JSON object/array
    3. Remove trailing commas and retry
    """

    if not text:
        return None

    cleaned = text.replace("```json", "").replace("```", "").strip()

    # First attempt: response is already valid JSON.
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Second attempt: find a JSON object or array inside the response.
    for start_char, end_char in (("{", "}"), ("[", "]")):

        start = cleaned.find(start_char)

        if start == -1:
            continue

        depth = 0
        in_string = False
        escape = False

        for i, ch in enumerate(cleaned[start:], start):

            if escape:
                escape = False
                continue

            if ch == "\\" and in_string:
                escape = True
                continue

            if ch == '"' and not escape:
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == start_char:
                depth += 1

            elif ch == end_char:
                depth -= 1

                if depth == 0:
                    candidate = cleaned[start : i + 1]

                    try:
                        return json.loads(candidate)

                    except json.JSONDecodeError:

                        repaired = re.sub(
                            r",\s*([}\]])",
                            r"\1",
                            candidate,
                        )

                        try:
                            return json.loads(repaired)
                        except json.JSONDecodeError:
                            break

    return None


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
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        json_output: bool = False,
    ):

        system_content = system_prompt or DEFAULT_SYSTEM_PROMPT

        if json_output:
            system_content = f"{system_content}\n\n" f"{JSON_INSTRUCTION}"

        response = await self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_content,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            response_format=({"type": "json_object"} if json_output else None),
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("LLM returned an empty response.")

        if json_output:

            result = _extract_json(content)

            if result is None:
                logger.error(
                    "LLM returned unparseable JSON: %s",
                    content,
                )

                raise ValueError("LLM did not return valid JSON.")

            return result

        return content.strip()

    """

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_output: bool = False
    ) -> str:
        logger.info("Sending request to Groq API")

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert assistant for summarizing "
                        "YouTube transcripts."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )

        logger.info("Received response from Groq API")

        #return response.choices[0].message.content

        content = response.choices[0].message.content
        if json_output:
            return json.loads(content)

        return content

    """


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
