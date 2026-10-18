from typing import Optional

from cache.memory_cache import MemoryCache
from pipeline.cleaning.cleaner import TranscriptCleaner
from storage.base_storage import BaseStorage
from storage.mongo_storage import MongoStorage
from video_processor.services.youtube_service import YoutubeTranscriptService
from video_processor.services.video_info import extract_chapters_and_info


class TranscriptService:
    def __init__(
        self,
        db: Optional[BaseStorage] = None,
        cache: Optional[MemoryCache] = None,
    ):
        self.cache = cache or MemoryCache()
        self.db = db or MongoStorage()

    def clean_transcript(self, transcript):
        for segment in transcript.segments:
            segment.text = TranscriptCleaner.clean(segment.text)

        return transcript

    def save(self, transcript):
        self.db.save(transcript)
        self.cache.set(f"transcript:{transcript.video_id}", transcript)

    def get(self, video_id):
        # 1. Cache
        transcript = self.cache.get(f"transcript:{video_id}")

        if transcript:
            print("Cache Hit")
            return transcript

        # 2. Database
        transcript = self.db.get(video_id)

        if transcript is not None:
            print("Loaded from DB")
            self.cache.set(f"transcript:{video_id}", transcript)
            return transcript

        # 3. YouTube - transcript
        fetch_service = YoutubeTranscriptService()
        transcript = fetch_service.fetch_transcript(video_id)

        if transcript is None:
            return None

        transcript = self.clean_transcript(transcript)

        # 4. YouTube - video metadata
        video_info = extract_chapters_and_info(video_id)
        transcript.video_info = video_info

        # 5. Save transcript + video_info
        self.save(transcript)

        return transcript

    def close(self):
        self.db.close()
