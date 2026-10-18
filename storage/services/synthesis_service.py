import asyncio
from typing import Optional

from cache.memory_cache import MemoryCache
from l6_layer import layer6_synthesis
from llm.groq_service import LLMService
from storage.mongo_storage import MongoStorage
from storage.services.ContentParseService import ContentParseService  # l2
from storage.services.KG_Service import KGService  # l3
from storage.services.deep_dive_service import DeepDiveService  # l5
from storage.services.transcript_service import TranscriptService


class SynthesisService:

    def __init__(
        self,
        db: Optional[MongoStorage] = None,
        cache: Optional[MemoryCache] = None,
    ):
        self.cache = cache or MemoryCache()
        self.db = db or MongoStorage()

        self.transcript_service = TranscriptService(db=self.db, cache=self.cache)

        # L2 service
        self.content_parse_service = ContentParseService(db=self.db, cache=self.cache)

        # L3 service
        self.kg_service = KGService(db=self.db, cache=self.cache)

        # L5 service
        self.deep_dive_service = DeepDiveService(db=self.db, cache=self.cache)

        self.llm_service = LLMService()

    def save(
        self,
        video_id: str,
        result: dict,
    ) -> None:

        # Cache
        self.cache.set(f"synthesis:{video_id}", result)

        # Database
        self.db.save_synthesis(
            video_id=video_id,
            result=result,
        )

    async def get(
        self,
        video_id: str,
        transcript=None,
        parsed=None,
        kg=None,
        sections=None,
    ) -> dict | None:

        # 1. Cache
        result = self.cache.get(f"synthesis:{video_id}")

        if result is not None:
            print("Cache Hit")
            return result

        # 2. Database
        result = self.db.get_synthesis(video_id)

        if result is not None:
            print("Loaded from DB")

            self.cache.set(
                f"synthesis:{video_id}",
                result,
            )

            return result

        # 3. Transcript
        if transcript is None:
            transcript = self.transcript_service.get(video_id)

        if transcript is None:
            return None

        # 4. L2 layer
        if parsed is None:
            parsed = await self.content_parse_service.get(
                video_id=video_id,
                transcript=transcript,
            )

        if parsed is None:
            return None

        # 5. L3 and L5 in parallel
        kg_task = (
            self.kg_service.get(
                video_id,
                transcript=transcript,
                layer2_result=parsed,
            )
            if kg is None
            else None
        )

        deep_dive_task = (
            self.deep_dive_service.get(
                video_id,
                transcript=transcript,
                parsed=parsed,
            )
            if sections is None
            else None
        )

        if kg_task and deep_dive_task:
            kg, sections = await asyncio.gather(kg_task, deep_dive_task)
        elif kg_task:
            kg = await kg_task
        elif deep_dive_task:
            sections = await deep_dive_task

        if kg is None or sections is None:
            return None

        # 6. L6 layer
        layer6_result = await layer6_synthesis(
            video_info=transcript.video_info or {},
            sections=sections,
            parsed=parsed,
            kg=kg,
            llm_service=self.llm_service,
        )

        # 7. Save L6 result
        self.save(
            video_id=video_id,
            result=layer6_result,
        )

        return layer6_result

    def close(self):
        self.db.close()

