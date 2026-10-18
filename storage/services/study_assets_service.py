import asyncio
from typing import Optional

from cache.memory_cache import MemoryCache
from l7_layer import layer7_study_assets
from llm.groq_service import LLMService
from storage.mongo_storage import MongoStorage
from storage.services.ContentParseService import ContentParseService  # l2
from storage.services.KG_Service import KGService  # l3
from storage.services.deep_dive_service import DeepDiveService  # l5
from storage.services.synthesis_service import SynthesisService  # l6
from storage.services.transcript_service import TranscriptService


class StudyAssetsService:

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

        # L6 service
        self.synthesis_service = SynthesisService(db=self.db, cache=self.cache)

        self.llm_service = LLMService()

    def save(
        self,
        video_id: str,
        result: dict,
    ) -> None:

        # Cache
        self.cache.set(f"study_assets:{video_id}", result)

        # Database
        self.db.save_study_assets(
            video_id=video_id,
            result=result,
        )

    async def get(
        self,
        video_id: str,
        sections=None,
        synthesis=None,
        kg=None,
        parsed=None,
    ) -> dict | None:

        # 1. Cache
        result = self.cache.get(f"study_assets:{video_id}")

        if result is not None:
            print("Cache Hit")
            return result

        # 2. Database
        result = self.db.get_study_assets(video_id)

        if result is not None:
            print("Loaded from DB")

            self.cache.set(
                f"study_assets:{video_id}",
                result,
            )

            return result

        # 3. L2 layer
        if parsed is None:
            parsed = await self.content_parse_service.get(video_id)

        if parsed is None:
            return None

        # 4. L3 and L5 in parallel
        kg_task = (
            self.kg_service.get(video_id, layer2_result=parsed)
            if kg is None
            else None
        )
        sections_task = (
            self.deep_dive_service.get(video_id, parsed=parsed)
            if sections is None
            else None
        )

        if kg_task and sections_task:
            kg, sections = await asyncio.gather(kg_task, sections_task)
        elif kg_task:
            kg = await kg_task
        elif sections_task:
            sections = await sections_task

        if kg is None or sections is None:
            return None

        # 5. L6 layer
        if synthesis is None:
            synthesis = await self.synthesis_service.get(
                video_id,
                parsed=parsed,
                kg=kg,
                sections=sections,
            )

        if synthesis is None:
            return None

        # 6. L7 layer
        layer7_result = await layer7_study_assets(
            sections=sections,
            synthesis=synthesis,
            kg=kg,
            parsed=parsed,
            llm_service=self.llm_service,
        )

        # 7. Save L7 result
        self.save(
            video_id=video_id,
            result=layer7_result,
        )

        return layer7_result

    def close(self):
        self.db.close()

