"""
from cache.memory_cache import MemoryCache
from processing.services.cleaner import TranscriptCleaner
from storage.sqlite_storage import SQLiteStorage
from video_processor.services.youtube_service import YoutubeTranscriptService


class TranscriptService:
    def __init__(self, db=None):
        self.cache = MemoryCache()
        self.db = db or SQLiteStorage()

    def clean_transcript(self, transcript):
        for segment in transcript.segments:
            segment.text = TranscriptCleaner.clean(segment.text)

        return transcript

    def get(self, video_id):

        # 1. Cache
        transcript = self.cache.get(video_id)

        if transcript:
            print("Cache Hit")
            return transcript

        # 2. Check database
        transcript = self.db.get(video_id)

        if transcript is not None:
            print("Loaded from DB")
            self.cache.set(video_id, transcript)
            return transcript

        # 3. Fetch from YouTube
        fetch_service = YoutubeTranscriptService()
        transcript = fetch_service.fetch_transcript(video_id)

        if transcript is None:
            return None

        # Clean transcript text
        transcript = self.clean_transcript(transcript)

        # 4. Save to database (full Transcript object, incl. segments)
        self.db.save(transcript)

        self.cache.set(video_id, transcript)

        return transcript

"""

from typing import Optional

from cache.memory_cache import MemoryCache
from pipeline.cleaning.cleaner import TranscriptCleaner
from storage.base_storage import BaseStorage
from storage.mongo_storage import MongoStorage
from video_processor.services.youtube_service import YoutubeTranscriptService
from video_processor.services.video_info import extract_chapters_and_info


class TranscriptService:
    def __init__(self, db: Optional[BaseStorage] = None):
        self.cache = MemoryCache()
        self.db = db or MongoStorage()

    def clean_transcript(self, transcript):
        for segment in transcript.segments:
            segment.text = TranscriptCleaner.clean(segment.text)

        return transcript

    def save(self, transcript):
        self.db.save(transcript)
        self.cache.set(transcript.video_id, transcript)

    def get(self, video_id):
        # 1. Cache
        transcript = self.cache.get(video_id)

        if transcript:
            print("Cache Hit")
            return transcript

        # 2. Database
        transcript = self.db.get(video_id)

        if transcript is not None:
            print("Loaded from DB")
            self.cache.set(video_id, transcript)
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
