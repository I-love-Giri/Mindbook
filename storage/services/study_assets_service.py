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

    def __init__(self, db: Optional[MongoStorage] = None):
        self.cache = MemoryCache()
        self.db = db or MongoStorage()

        self.transcript_service = TranscriptService(db=self.db)

        # L2 service
        self.content_parse_service = ContentParseService(db=self.db)

        # l3
        self.kg_service = KGService(db=self.db)

        # l5
        self.deep_dive_service = DeepDiveService(db=self.db)

        # l6
        self.synthesis_service = SynthesisService(db=self.db)

        self.llm_service = LLMService()

    def save(
        self,
        video_id: str,
        result: dict,
    ) -> None:

        # Cache
        self.cache.set(video_id, result)

        # Database
        self.db.save_study_assets(
            video_id=video_id,
            result=result,
        )

    async def get(
        self,
        video_id: str,
    ) -> dict | None:

        # 1. Cache
        result = self.cache.get(video_id)

        if result is not None:
            print("Cache Hit")
            return result

        # 2. Database
        result = self.db.get_study_assets(video_id)

        if result is not None:
            print("Loaded from DB")

            self.cache.set(
                video_id,
                result,
            )

            return result

        # 3. Transcript
        transcript = self.transcript_service.get(video_id)

        if transcript is None:
            return None

        # 4. L2 layer
        layer2_result = await self.content_parse_service.get(video_id)

        if layer2_result is None:
            return None

        # 5. L3 layer

        layer3_result = await self.kg_service.get(video_id)

        if layer3_result is None:
            return None

        # 6. l5 layer

        layer5_result = await self.deep_dive_service.get(video_id)

        if layer5_result is None:
            return None

        # 7. l6 layer

        layer6_result = await self.synthesis_service.get(video_id)

        if layer6_result is None:
            return None

        # 8. l7 layer

        layer7_result = await layer7_study_assets(
            sections=layer5_result,
            synthesis=layer6_result,
            kg=layer3_result,
            parsed=layer2_result,
            llm_service=self.llm_service,
        )

        # 6. Save L6 result
        self.save(
            video_id=video_id,
            result=layer7_result,
        )

        return layer7_result

    def close(self):
        self.db.close()
