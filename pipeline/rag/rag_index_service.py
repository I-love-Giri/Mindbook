from typing import List, Dict

from pipeline.embeddings.embedder import EmbeddingService
from pipeline.vectorstore.qdrant_store import QdrantStore


class RAGIndexService:

    def __init__(self, store: QdrantStore):
        self.embedding_service = EmbeddingService()
        self.store = store

    def index_chunks(self, chunks: List[Dict]) -> None:
        if not chunks:
            return

        vectors = self.embedding_service.embed_chunks(chunks)

        self.store.upsert(
            chunks=chunks,
            vectors=vectors,
        )

        print(f"Indexed {len(chunks)} chunks into Qdrant.")

    def close(self):
        pass
