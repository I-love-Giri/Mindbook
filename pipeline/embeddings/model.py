from google import genai

from config.settings import GEMINI_API_KEY


def create_embedding_model(
    model_name: str = "gemini-embedding-2",
):
    return genai.Client(
        api_key=GEMINI_API_KEY,
    )
