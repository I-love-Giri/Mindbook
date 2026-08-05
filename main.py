import json
import os
from pprint import pprint
import sys
from pipeline.chunking.chunker import TranscriptChunker
from pipeline.embeddings.embedder import EmbeddingService
from pipeline.rag.context_builder import ContextBuilder
from pipeline.rag.generator import Generator
from pipeline.retrieval.retriever import Retriever
from pipeline.vectorstore.qdrant_store import QdrantStore
from video_processor.services.parser import extract_video_id
from video_processor.services.youtube_service import YoutubeTranscriptService

if __name__ == "__main__":

    url = input("Enter the URL: ").strip()

    if not url:
        print("URL cannot be empty")
        exit(1)

    id = extract_video_id(url)
    print(f"Video ID: {id}")

    service = YoutubeTranscriptService()
    transcript = service.fetch_transcript(id)

    chunking = TranscriptChunker(3)
    result = chunking.chunk(transcript.segments, transcript.video_id)

    embedding_service = EmbeddingService()

    vectors = embedding_service.embed_chunks(result)

    store = QdrantStore()

    store.delete_collection()

    store.upsert(result, vectors)

    # pprint(result[0])

    print("Video indexed successfully!")

    retriever = Retriever(embedding_service, store)

    generator = Generator()

    while True:

        query = input("\nAsk a question (or 'exit'): ")

        if query.lower() == "exit":
            break

        results = retriever.retrieve(query, limit=5)

        context_builder = ContextBuilder()

        context = context_builder.build(results)

        answer = generator.generate(query, context)

        print("\nAnswer:")
        print(answer)

        # print(context)

        """
        pprint(results)

        print("\nRetrieved Chunks:\n")

        for i, chunk in enumerate(results, 1):

            print(f"----- Chunk {i} -----")
            print(f"Score: {chunk['score']:.4f}")
            print(f"Time: {chunk['start']} - {chunk['end']}")
            print(chunk["text"])
            print()
        """

    if os.path.exists(f"{id}_chunking.json"):
        with open(f"{id}_chunking.json", "r", encoding="utf-8") as f:
            old_result = json.load(f)

        start_id = len(old_result) + 1

        for index, chunk in enumerate(result):
            chunk["chunk_id"] = start_id + index

        old_result.extend(result)
    else:
        old_result = result

    with open(f"{id}_chunking.json", "w", encoding="utf-8") as f:
        json.dump(old_result, f, ensure_ascii=False, indent=2)

    print(f"Saved: {id}_chunking.json")
