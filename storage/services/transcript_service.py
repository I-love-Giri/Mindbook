from storage.sqlite_storage import SQLiteStorage
from video_processor.services.youtube_service import YoutubeTranscriptService


class TranscriptService:
    def __init__(self, db=None):
        self.db = db or SQLiteStorage()

    def get(self, video_id):

        # 1. Check database
        transcript = self.db.get(video_id)

        if transcript is not None:
            print("Loaded from DB")
            return transcript

        # 2. Fetch from YouTube
        fetch_service = YoutubeTranscriptService()
        transcript = fetch_service.fetch_transcript(video_id)

        if transcript is None:
            return None

        # 3. Save to database
        self.db.save(
            transcript.video_id,
            transcript.language,
            transcript.language_code,
            transcript.text,
        )

        return transcript

