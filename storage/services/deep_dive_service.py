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

    # --------------------------------------------------
    # Save complete L5 result for one video
    # --------------------------------------------------

    def save(
        self,
        video_id: str,
        results: list[dict],
    ) -> None:

        # Cache whole video result
        self.cache.set(
            video_id,
            results,
        )

        # MongoDB: ONE document per video
        self.db.save_deep_dive(
            video_id=video_id,
            results=results,
        )

    # --------------------------------------------------
    # Get Deep Dive
    # --------------------------------------------------

    async def get(
        self,
        video_id: str,
    ) -> list[dict] | None:

        # --------------------------------------------------
        # 1. Check cache
        # --------------------------------------------------

        cached = self.cache.get(video_id)

        if cached is not None:

            print("Cache Hit")

            return cached

        # --------------------------------------------------
        # 2. Check MongoDB
        # --------------------------------------------------

        stored = self.db.get_deep_dive(video_id)

        if stored is not None:

            print("Loaded from DB")

            self.cache.set(
                video_id,
                stored,
            )

            return stored

        # --------------------------------------------------
        # 3. Get transcript from L1
        # --------------------------------------------------

        transcript = self.transcript_service.get(video_id)

        if transcript is None:
            return None

        # --------------------------------------------------
        # 4. Get L2 parsed content
        # --------------------------------------------------

        parsed = await self.content_parse_service.get(video_id)

        if parsed is None:
            return None

        # --------------------------------------------------
        # 5. Video information
        # --------------------------------------------------

        video_info = transcript.video_info or {}

        # --------------------------------------------------
        # 6. Create chunks
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
        # 7. Process chunks in REAL batches
        # --------------------------------------------------

        all_results = []

        for start in range(
            0,
            len(chunks),
            self.BATCH_SIZE,
        ):

            batch = chunks[start : start + self.BATCH_SIZE]

            print(
                f"\nRunning L5 batch "
                f"{start + 1}-"
                f"{start + len(batch)}/"
                f"{len(chunks)}"
            )

            for chunk in batch:

                print(f"  → [{chunk['chunk_id']}] " f"{chunk.get('title', 'Untitled')}")

            # --------------------------------------------------
            # ONE LLM CALL FOR WHOLE BATCH
            # --------------------------------------------------

            batch_results = await layer5_deep_dive(
                chunks=batch,
                video_info=video_info,
                parsed=parsed,
                llm_service=self.llm_service,
            )

            # --------------------------------------------------
            # Add batch results
            # --------------------------------------------------

            all_results.extend(batch_results)

            print("✓ Batch completed")

        # --------------------------------------------------
        # 8. Save ONE document
        # --------------------------------------------------

        self.save(
            video_id=video_id,
            results=all_results,
        )

        # --------------------------------------------------
        # 9. Return
        # --------------------------------------------------

        return all_results

    # --------------------------------------------------
    # Close
    # --------------------------------------------------

    def close(self):
        self.db.close()
