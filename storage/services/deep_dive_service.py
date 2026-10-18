from typing import Awaitable, Callable, Optional
import asyncio
import inspect

from cache.memory_cache import MemoryCache
from l5_layer import layer5_deep_dive
from llm.openrouter_service import OpenrouterService
from pipeline.chunking.chunker import TranscriptChunker
from pipeline.rag.rag_index_service import RAGIndexService
from storage.mongo_storage import MongoStorage
from storage.services.ContentParseService import ContentParseService
from storage.services.transcript_service import TranscriptService


class DeepDiveService:
    BATCH_SIZE = 1
    REQUEST_GAP_SECONDS = 1.5

    def __init__(
        self,
        db: Optional[MongoStorage] = None,
        rag_index_service: Optional[RAGIndexService] = None,
        embedding_model=None,
        cache: Optional[MemoryCache] = None,
    ):
        # -----------------------------------------------------
        # Cache
        # -----------------------------------------------------

        self.cache = cache or MemoryCache()

        # -----------------------------------------------------
        # Database
        # -----------------------------------------------------

        self.db = db or MongoStorage()

        # -----------------------------------------------------
        # Dependent services
        # -----------------------------------------------------

        self.transcript_service = TranscriptService(db=self.db, cache=self.cache)

        self.content_parse_service = ContentParseService(db=self.db, cache=self.cache)

        # -----------------------------------------------------
        # L5 LLM
        # -----------------------------------------------------

        self.llm_service = OpenrouterService()

        # -----------------------------------------------------
        # Optional RAG dependencies
        # -----------------------------------------------------

        self.rag_index_service = rag_index_service
        self.embedding_model = embedding_model

    # =========================================================
    # CACHE
    # =========================================================

    def save(
        self,
        video_id: str,
        results: list[dict],
    ) -> None:

        self.cache.set(
            f"deep_dive:{video_id}",
            results,
        )

        # NOTE:
        # We intentionally DO NOT save the whole video
        # to MongoDB here anymore.
        #
        # Each L5 chunk is saved separately using:
        #
        # self.db.save_deep_dive_chunk(...)
        #
        # This method is now only useful for cache updates.

    # =========================================================
    # GET / RUN L5
    # =========================================================

    async def get(
        self,
        video_id: str,
        on_batch: (
            Callable[
                [list[dict], int, int],
                Awaitable[None] | None,
            ]
            | None
        ) = None,
        transcript=None,
        parsed=None,
    ) -> list[dict] | None:

        # =====================================================
        # 1. CHECK MEMORY CACHE
        # =====================================================

        cached = self.cache.get(f"deep_dive:{video_id}")

        if cached is not None:

            print("Cache Hit")

            if on_batch:

                for index, item in enumerate(cached):

                    emitted = on_batch(
                        [item],
                        index,
                        len(cached),
                    )

                    if inspect.isawaitable(emitted):
                        await emitted

            return cached

        # =====================================================
        # 2. GET TRANSCRIPT & VIDEO INFO
        # =====================================================

        if transcript is None:
            transcript = self.transcript_service.get(video_id)

        if transcript is None:
            return None

        video_info = transcript.video_info or {}

        # =====================================================
        # 3. CREATE CHUNKER & CHUNKS
        # =====================================================

        chunker = TranscriptChunker(
            version=TranscriptChunker.VERSION_SEMANTIC,
            max_words=300,
            overlap_words=50,
            embedding_model=self.embedding_model,
        )

        chunks = chunker.chunk(
            segments=transcript.segments,
            video_id=video_id,
            chapters=video_info.get("chapters"),
            duration=video_info.get("duration"),
        )

        print(f"\nGenerated {len(chunks)} chunks")

        # =====================================================
        # 4. CHECK MONGODB (Verify ALL chunks are present)
        # =====================================================

        stored = self.db.get_deep_dive(video_id)

        if stored and len(stored) == len(chunks):

            print("Loaded from DB (All chunks completed)")

            self.cache.set(
                f"deep_dive:{video_id}",
                stored,
            )

            if on_batch:

                for index, item in enumerate(stored):

                    emitted = on_batch(
                        [item],
                        index,
                        len(stored),
                    )

                    if inspect.isawaitable(emitted):
                        await emitted

            return stored

        # =====================================================
        # 5. GET L2 PARSED CONTENT (if not already provided)
        # =====================================================

        if parsed is None:
            parsed = await self.content_parse_service.get(
                video_id=video_id,
                transcript=transcript,
            )

        if parsed is None:
            return None

        # =====================================================
        # 6. INDEX CHUNKS IN RAG
        # =====================================================

        if self.rag_index_service is not None:

            self.rag_index_service.index_chunks(chunks)

        # =====================================================
        # 9. PROCESS CHUNKS
        # =====================================================

        for start in range(
            0,
            len(chunks),
            self.BATCH_SIZE,
        ):

            batch = chunks[start : start + self.BATCH_SIZE]

            # -------------------------------------------------
            # Current BATCH_SIZE = 1
            # -------------------------------------------------

            for batch_offset, chunk in enumerate(batch):

                chunk_id = chunk["chunk_id"]

                chunk_index = start + batch_offset

                print(
                    f"\nChecking chunk "
                    f"{chunk_index + 1}/"
                    f"{len(chunks)}: "
                    f"{chunk_id}"
                )

                # =============================================
                # 9A. CHECK IF CHUNK ALREADY EXISTS
                # =============================================

                existing = self.db.get_deep_dive_chunk(
                    video_id=video_id,
                    chunk_id=chunk_id,
                )

                if existing is not None:

                    print(f"✓ Skipping {chunk_id} " f"— already completed")

                    # -----------------------------------------
                    # Emit existing result
                    # -----------------------------------------

                    if on_batch:

                        emitted = on_batch(
                            [existing],
                            chunk_index,
                            len(chunks),
                        )

                        if inspect.isawaitable(emitted):
                            await emitted

                    continue

                # =============================================
                # 9B. RUN L5
                # =============================================

                print(f"→ Running L5 for {chunk_id}")

                batch_results = await layer5_deep_dive(
                    chunks=batch,
                    video_info=video_info,
                    parsed=parsed,
                    llm_service=self.llm_service,
                )

                # =============================================
                # 9C. SAVE EACH RESULT IMMEDIATELY
                # =============================================

                for result_offset, result in enumerate(batch_results):

                    result_chunk_id = result["chunk_id"]

                    result_chunk_index = chunk_index + result_offset

                    self.db.save_deep_dive_chunk(
                        video_id=video_id,
                        chunk_id=result_chunk_id,
                        chunk_index=result_chunk_index,
                        result=result,
                    )

                    print(f"✓ Saved " f"{result_chunk_id} " f"to MongoDB")

                # =============================================
                # 9D. EMIT RESULT
                # =============================================

                if on_batch and batch_results:

                    emitted = on_batch(
                        batch_results,
                        chunk_index,
                        len(chunks),
                    )

                    if inspect.isawaitable(emitted):
                        await emitted

                print("✓ Chunk completed")

            # =================================================
            # 10. REQUEST GAP
            # =================================================

            if start + self.BATCH_SIZE < len(chunks):

                await asyncio.sleep(self.REQUEST_GAP_SECONDS)

        # =====================================================
        # 11. LOAD ALL COMPLETED RESULTS
        # =====================================================

        all_results = self.db.get_deep_dive(video_id)

        # =====================================================
        # 12. UPDATE CACHE
        # =====================================================

        self.cache.set(
            f"deep_dive:{video_id}",
            all_results,
        )

        # =====================================================
        # 13. RETURN
        # =====================================================

        return all_results

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self) -> None:

        if self.rag_index_service is not None:
            self.rag_index_service.close()

        self.db.close()
