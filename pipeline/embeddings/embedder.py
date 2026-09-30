from typing import List, Dict

import torch
from sentence_transformers import SentenceTransformer


class EmbeddingService:

    def __init__(
        self,
        model: SentenceTransformer | None = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        if model is not None:
            self.model = model
        else:
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self.model = SentenceTransformer(model_name, device=device)

    def embed_chunks(self, chunks: List[Dict]) -> List[List[float]]:

        texts = [chunk["text"] for chunk in chunks]

        embeddings = self.model.encode(
            texts,
            batch_size=20,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:

        embedding = self.model.encode(
            query,
            normalize_embeddings=True,
        )

        return embedding.tolist()
