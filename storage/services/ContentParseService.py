from typing import Optional

from cache.memory_cache import MemoryCache
from l2_layer import layer2_content_parse
from llm.groq_service import LLMService
from storage.mongo_storage import MongoStorage
from storage.services.transcript_service import TranscriptService


class ContentParseService:

    def __init__(self, db: Optional[MongoStorage] = None):
        self.cache = MemoryCache()
        self.db = db or MongoStorage()

        self.transcript_service = TranscriptService(db=self.db)

        self.llm_service = LLMService()

    def save(
        self,
        video_id: str,
        result: dict,
    ) -> None:

        # Cache
        self.cache.set(video_id, result)

        # Database
        self.db.save_content_parse(
            video_id=video_id,
            result=result,
        )

    async def get(
        self,
        video_id: str,
        transcript=None,
    ) -> dict | None:

        # 1. Cache
        result = self.cache.get(video_id)

        if result is not None:
            return result

        # 2. Database
        result = self.db.get_content_parse(video_id)

        if result is not None:
            self.cache.set(video_id, result)
            return result

        # 3. Transcript
        if transcript is None:
            transcript = self.transcript_service.get(video_id)

        if transcript is None:
            return None

        # 4. L2
        layer2_result = await layer2_content_parse(
            transcript=transcript,
            video_info=transcript.video_info or {},
            llm_service=self.llm_service,
        )

        # 5. Save
        self.save(
            video_id=video_id,
            result=layer2_result,
        )

        return layer2_result
