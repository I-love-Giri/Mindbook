import asyncio
from typing import Optional

from cache.memory_cache import MemoryCache
from l5_layer import layer5_deep_dive
from llm.groq_service import LLMService
from pipeline.chunking.chunker import TranscriptChunker
from storage.mongo_storage import MongoStorage
from storage.services.ContentParseService import ContentParseService
from storage.services.transcript_service import TranscriptService


class DeepDiveService:

    BATCH_SIZE = 3

    def __init__(self, db: Optional[MongoStorage] = None):
        self.cache = MemoryCache()
        self.db = db or MongoStorage()

        self.transcript_service = TranscriptService(db=self.db)
        self.content_parse_service = ContentParseService(db=self.db)

        self.llm_service = LLMService()

    def save(
        self,
        video_id: str,
        chunk_id: str,
        result: dict,
    ) -> None:

        cache_key = f"{video_id}:{chunk_id}"

        # Cache
        self.cache.set(
            cache_key,
            result,
        )

        # Database
        self.db.save_deep_dive(
            video_id=video_id,
            chunk_id=chunk_id,
            result=result,
        )

    async def get(self, video_id: str) -> list[dict] | None:

        # --------------------------------------------------
        # 1. Get transcript
        # --------------------------------------------------

        transcript = self.transcript_service.get(video_id)

        if transcript is None:
            return None

        # --------------------------------------------------
        # 2. Get L2 parsed content
        # --------------------------------------------------

        parsed = await self.content_parse_service.get(video_id)

        if parsed is None:
            return None

        # --------------------------------------------------
        # 3. Video information
        # --------------------------------------------------

        video_info = transcript.video_info or {}

        # --------------------------------------------------
        # 4. Create chunks
        # --------------------------------------------------

        chunker = TranscriptChunker(
            version=TranscriptChunker.VERSION_SEMANTIC,
            max_words=300,
            overlap_words=50,
        )

        chunks = chunker.chunk(
            segments=transcript.segments,
            video_id=video_id,
            chapters=video_info.get("chapters"),
            duration=video_info.get("duration"),
        )

        print(f"\nGenerated {len(chunks)} chunks")

        # --------------------------------------------------
        # 5. Check cache + DB
        # --------------------------------------------------

        results_by_chunk = {}
        missing_chunks = []

        for chunk in chunks:

            chunk_id = chunk["chunk_id"]
            cache_key = f"{video_id}:{chunk_id}"

            # -----------------------------
            # Cache
            # -----------------------------

            result = self.cache.get(cache_key)

            if result is not None:

                print(f"Cache Hit: {chunk_id}")

                results_by_chunk[chunk_id] = result

                continue

            # -----------------------------
            # MongoDB
            # -----------------------------

            result = self.db.get_deep_dive(
                video_id=video_id,
                chunk_id=chunk_id,
            )

            if result is not None:

                print(f"Loaded from DB: {chunk_id}")

                self.cache.set(
                    cache_key,
                    result,
                )

                results_by_chunk[chunk_id] = result

                continue

            # -----------------------------
            # Missing
            # -----------------------------

            missing_chunks.append(chunk)

        print(f"\nExisting L5 results: {len(results_by_chunk)}")
        print(f"Missing L5 results: {len(missing_chunks)}")

        # --------------------------------------------------
        # 6. Process missing chunks in batches
        # --------------------------------------------------

        for start in range(
            0,
            len(missing_chunks),
            self.BATCH_SIZE,
        ):

            batch = missing_chunks[start : start + self.BATCH_SIZE]

            print(
                f"\nRunning L5 batch "
                f"{start + 1}-"
                f"{start + len(batch)}/"
                f"{len(missing_chunks)}"
            )

            # Show chunks
            for chunk in batch:
                print(f"  → [{chunk['chunk_id']}] " f"{chunk.get('title', 'Untitled')}")

            # --------------------------------------------------
            # Run L5 concurrently
            # --------------------------------------------------

            tasks = [
                layer5_deep_dive(
                    chunk=chunk,
                    video_info=video_info,
                    parsed=parsed,
                    llm_service=self.llm_service,
                )
                for chunk in batch
            ]

            batch_results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            # --------------------------------------------------
            # Save results
            # --------------------------------------------------

            for chunk, result in zip(batch, batch_results):

                chunk_id = chunk["chunk_id"]

                # If one LLM call failed, don't crash the
                # entire DeepDive pipeline.
                if isinstance(result, Exception):

                    print(f"✗ L5 failed for chunk " f"{chunk_id}: {result}")

                    continue

                self.save(
                    video_id=video_id,
                    chunk_id=chunk_id,
                    result=result,
                )

                results_by_chunk[chunk_id] = result

            print("✓ Batch completed")

        # --------------------------------------------------
        # 7. Return results in chunk order
        # --------------------------------------------------

        results = []

        for chunk in chunks:

            chunk_id = chunk["chunk_id"]

            if chunk_id in results_by_chunk:

                results.append(
                    {
                        "chunk_id": chunk_id,
                        "result": results_by_chunk[chunk_id],
                    }
                )

        # --------------------------------------------------
        # 8. Return
        # --------------------------------------------------

        return results

    def close(self):
        self.db.close()
