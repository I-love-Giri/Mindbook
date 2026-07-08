from cache.memory_cache import MemoryCache
from storage.sqlite_storage import SQLiteStorage
from video_processor.services.youtube_service import YoutubeTranscriptService


class TranscriptService:
    def __init__(self, db=None):
        self.cache = MemoryCache()
        self.db = db or SQLiteStorage()

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

        # 4. Save to database (full Transcript object, incl. segments)
        self.db.save(transcript)

        self.cache.set(video_id, transcript)

        return transcript

