from typing import List

from pipeline.embeddings.embedder import EmbeddingService
from pipeline.vectorstore.qdrant_store import QdrantStore


class Retriever:

    def __init__(self, embedding_service: EmbeddingService, vector_store: QdrantStore):

        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(self, query: str, limit: int = 5) -> List[dict]:

        query_vector = self.embedding_service.embed_query(query)

        results = self.vector_store.search(query_vector=query_vector, limit=limit)

        return [
            {
                **result.payload,
                "score": result.score,
            }
            for result in results
        ]
