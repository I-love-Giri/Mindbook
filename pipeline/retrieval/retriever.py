"""from typing import List

from pipeline.embeddings.embedder import EmbeddingService
from pipeline.vectorstore.qdrant_store import QdrantStore


class Retriever:

    def __init__(self, embedding_service: EmbeddingService, vector_store: QdrantStore):

        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        video_id: str,
        limit: int = 5,
    ) -> List[dict]:

        query_vector = self.embedding_service.embed_query(query)

        results = self.vector_store.search(
            query_vector=query_vector,
            video_id=video_id,
            limit=limit,
        )

        return [
            {
                **result.payload,
                "score": result.score,
            }
            for result in results
        ]
"""

import logging
from typing import List

from pipeline.embeddings.embedder import EmbeddingService
from pipeline.vectorstore.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


class Retriever:

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: QdrantStore,
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        video_id: str,
        limit: int = 5,
    ) -> List[dict]:

        query_vector = self.embedding_service.embed_query(query)

        results = self.vector_store.search(
            query_vector=query_vector,
            video_id=video_id,
            limit=limit,
        )

        chunks = []

        for result in results:
            chunk = {
                **result.payload,
                "score": result.score,
            }

            chunks.append(chunk)

            logger.info(
                "RAG Retrieved | video=%s | chunk=%s | score=%.4f | text=%s",
                video_id,
                chunk.get("chunk_id"),
                result.score,
                chunk.get("text", "")[:120].replace("\n", " "),
            )

        return chunks
