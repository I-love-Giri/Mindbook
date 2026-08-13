from pymongo import MongoClient
from storage.base_storage import BaseStorage
from video_processor.models.transcript import Segment, Transcript


class MongoStorage(BaseStorage):
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017/",
        database: str = "video_processor",
        collection: str = "transcripts",
    ):
        self.client = MongoClient(uri)
        self.db = self.client[database]
        self.collection = self.db[collection]

        self.collection.create_index("video_id", unique=True)

    def save(self, transcript: Transcript) -> None:
        document = {
            "video_id": transcript.video_id,
            "language": transcript.language,
            "language_code": transcript.language_code,
            "summary": transcript.summary,
            "video_info": transcript.video_info,
            "segments": [
                {
                    "text": segment.text,
                    "start": segment.start,
                    "duration": segment.duration,
                }
                for segment in transcript.segments
            ],
        }

        self.collection.replace_one(
            {"video_id": transcript.video_id},
            document,
            upsert=True,
        )

    def get(self, video_id: str):
        document = self.collection.find_one({"video_id": video_id})

        if document is None:
            return None

        segments = [
            Segment(
                text=segment["text"],
                start=segment["start"],
                duration=segment["duration"],
            )
            for segment in document.get("segments", [])
        ]

        return Transcript(
            video_id=document["video_id"],
            language=document["language"],
            language_code=document["language_code"],
            segments=segments,
            summary=document.get("summary"),
            video_info=document.get("video_info"),
        )

    def close(self) -> None:
        self.client.close()
