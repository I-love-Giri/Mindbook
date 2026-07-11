from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME


class LLMService:

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(self,prompt: str, temperature: float = 0.7, max_tokens: int = 1024)-> str:

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

        return response.choices[0].message.content

'''

llm = LLMService()

answer = llm.generate(
    "Explain Python in one paragraph."
)

print(answer)

Output: 

Python is a high‑level, interpreted programming language known for its clean, readable syntax and strong emphasis on code readability, which makes it an excellent choice for both beginners and experienced developers. It supports multiple programming paradigms—including procedural, object‑oriented, and functional styles—and comes with a massive standard library plus a vibrant ecosystem of third‑party packages for tasks ranging from web development and data analysis to machine learning and automation. Python’s dynamic typing, automatic memory management, and interactive interpreter enable rapid development and prototyping, while its cross‑platform nature ensures code can run on Windows, macOS, Linux, and many other systems with little or no modification.

'''
