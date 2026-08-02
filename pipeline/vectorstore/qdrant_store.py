from typing import List, Dict
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class QdrantStore:

    def __init__(
        self,
        collection_name: str = "transcripts",
        host: str = "localhost",
        port: int = 6333,
    ):

        self.collection_name = collection_name

        # self.client = QdrantClient(host=host, port=port)

        self.client = QdrantClient(path="./qdrant_data")

    def create_collection(self, vector_size: int):

        if self.client.collection_exists(self.collection_name):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert(self, chunks: List[Dict], vectors: List[List[float]]):

        if len(chunks) != len(vectors):
            raise ValueError("Chunks and vectors must have the same length.")

        if not vectors:
            return

        if not self.client.collection_exists(self.collection_name):
            self.create_collection(vector_size=len(vectors[0]))

        points = []

        for chunk, vector in zip(chunks, vectors):

            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL, f"{chunk['video_id']}_{chunk['chunk_id']}"
                )
            )

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "video_id": chunk["video_id"],
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "start": chunk["start"],
                        "end": chunk["end"],
                        "word_count": chunk["word_count"],
                    },
                )
            )

        self.client.upsert(
            collection_name=self.collection_name, points=points, wait=True
        )

    def search(self, query_vector: List[float], limit: int = 5):

        return self.client.query_points(
            collection_name=self.collection_name, query=query_vector, limit=limit
        ).points

    def delete_collection(self):

        self.client.delete_collection(self.collection_name)
