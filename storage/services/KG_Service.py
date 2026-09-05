from typing import Optional

from cache.memory_cache import MemoryCache
from l3_layer import layer3_knowledge_graph
from llm.groq_service import LLMService
from storage.mongo_storage import MongoStorage
from storage.services.ContentParseService import ContentParseService
from storage.services.transcript_service import TranscriptService


class KGService:

    def __init__(self, db: Optional[MongoStorage] = None):
        self.cache = MemoryCache()
        self.db = db or MongoStorage()

        self.transcript_service = TranscriptService(db=self.db)

        # L2 service
        self.content_parse_service = ContentParseService(db=self.db)

        self.llm_service = LLMService()

    def save(
        self,
        video_id: str,
        result: dict,
    ) -> None:

        # Cache
        self.cache.set(video_id, result)

        # Database
        self.db.save_knowledge_graph(
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
        result = self.db.get_knowledge_graph(video_id)

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

        # 5. L3
        layer3_result = await layer3_knowledge_graph(
            layer2_result=layer2_result,
            transcript=transcript.segments,
            video_info=transcript.video_info or {},
            llm_service=self.llm_service,
        )

        # 6. Save L3 result
        self.save(
            video_id=video_id,
            result=layer3_result,
        )

        return layer3_result

    def close(self):
        self.db.close()
