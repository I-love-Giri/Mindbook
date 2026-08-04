import logging
from groq import APIConnectionError, APITimeoutError, Groq, RateLimitError


from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)


from config.settings import GROQ_API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)


class Generator:
    def __init__(self):
        self.client = Groq(
            api_key=GROQ_API_KEY,
            # max_retries= 3,  # SDK handles transient retries
            timeout=30.0,  # Prevent requests from hanging indefinitely
        )

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
    def generate(self, question: str, context: str) -> str:
        prompt = f"""
            You are a helpful assistant.

            Answer the user's question in simple , use the provided context , and if possible then explain things using real life examples.
            If the answer cannot be found in the context, say:
            "I couldn't find that information in the transcript."

            Context:
            {context}

            Question:
            {question}
            """

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You answer questions about YouTube video transcripts.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()
