from typing import List, Dict

from google import genai

from config.settings import GEMINI_API_KEY


class EmbeddingService:

    def __init__(
        self,
        model_name: str = "gemini-embedding-2",
    ):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = model_name

    def embed_chunks(self, chunks: List[Dict]) -> List[List[float]]:

        texts = [chunk["text"] for chunk in chunks]

        result = self.client.models.embed_content(
            model=self.model_name,
            contents=texts,
        )

        return [embedding.values for embedding in result.embeddings]

    def embed_query(self, query: str) -> List[float]:

        result = self.client.models.embed_content(
            model=self.model_name,
            contents=query,
        )

        return result.embeddings[0].values
