from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_SITE_URL = os.getenv(
    "OPENROUTER_SITE_URL",
    "http://localhost:8000",
)

OPENROUTER_APP_NAME = os.getenv(
    "OPENROUTER_APP_NAME",
    "MindBook",
)


OPENROUTER_TEXT_MODELS = [
    model.strip()
    for model in os.getenv(
        "OPENROUTER_TEXT_MODELS",
        "openrouter/free",
    ).split(",")
    if model.strip()
]

OPENROUTER_FAST_MODELS = [
    model.strip()
    for model in os.getenv(
        "OPENROUTER_FAST_MODELS",
        "openrouter/free",
    ).split(",")
    if model.strip()
]
