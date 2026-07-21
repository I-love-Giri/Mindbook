import logging
import json

from groq import Groq

'''
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)
'''

from config.settings import GROQ_API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = Groq(
            api_key=GROQ_API_KEY,
            max_retries= 3,  # SDK handles transient retries
            timeout= 30.0,    # Prevent requests from hanging indefinitely
        )

    '''
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(
            (
                APIConnectionError,
                APITimeoutError,
                RateLimitError,
            )
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    
    '''

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

'''

llm = LLMService()

answer = llm.generate(
    "Explain Python in one paragraph."
)

print(answer)

Output: 

Python is a high‑level, interpreted programming language known for its clean, readable syntax and strong emphasis on code readability, which makes it an excellent choice for both beginners and experienced developers. It supports multiple programming paradigms—including procedural, object‑oriented, and functional styles—and comes with a massive standard library plus a vibrant ecosystem of third‑party packages for tasks ranging from web development and data analysis to machine learning and automation. Python’s dynamic typing, automatic memory management, and interactive interpreter enable rapid development and prototyping, while its cross‑platform nature ensures code can run on Windows, macOS, Linux, and many other systems with little or no modification.

'''
'''
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

'''