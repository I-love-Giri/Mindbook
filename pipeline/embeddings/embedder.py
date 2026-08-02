from typing import List, Dict

import torch
from sentence_transformers import SentenceTransformer


class EmbeddingService:

    def __init__(self, model_name="Qwen/Qwen3-Embedding-0.6B"):

        device = "mps" if torch.backends.mps.is_available() else "cpu"

        self.model = SentenceTransformer(model_name, device=device)

    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:

        texts = [chunk["text"] for chunk in chunks]

        embeddings = self.model.encode(
            texts, batch_size=8, normalize_embeddings=True, show_progress_bar=True
        )

        return embeddings.tolist()

    def embed_query(self, query: str):

        return self.model.encode(query, normalize_embeddings=True)
