from pymongo import MongoClient
from storage.base_storage import BaseStorage
from video_processor.models.transcript import Segment, Transcript


class MongoStorage(BaseStorage):
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017/",
        database: str = "video_processor",
        collection: str = "transcripts",
        content_parse_collection: str = "content_parse",
        knowledge_graph_collection: str = "Knowledge_graph",
    ):
        self.client = MongoClient(uri)
        self.db = self.client[database]
        self.collection = self.db[collection]
        self.content_parse = self.db[content_parse_collection]
        self.knowledge_graph = self.db[knowledge_graph_collection]

        self.collection.create_index("video_id", unique=True)

        self.content_parse.create_index(
            "video_id",
            unique=True,
        )

    def save(self, transcript: Transcript) -> None:
        document = {
            "video_id": transcript.video_id,
            "language": transcript.language,
            "language_code": transcript.language_code,
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
            video_info=document.get("video_info"),
        )

    # ---------------------------------------------------------
    # L2 Content Parse
    # ---------------------------------------------------------

    def save_content_parse(
        self,
        video_id: str,
        result: dict,
    ) -> None:

        document = {
            "video_id": video_id,
            "result": result,
        }

        self.content_parse.replace_one(
            {"video_id": video_id},
            document,
            upsert=True,
        )

    def get_content_parse(
        self,
        video_id: str,
    ) -> dict | None:

        document = self.content_parse.find_one({"video_id": video_id})

        if document is None:
            return None

        return document.get("result")

    # ---------------------------------------------------------
    # L3 Knowledge Parse
    # ---------------------------------------------------------

    def save_knowledge_graph(
        self,
        video_id: str,
        result: dict,
    ) -> None:

        document = {
            "video_id": video_id,
            "result": result,
        }

        self.knowledge_graph.replace_one(
            {"video_id": video_id},
            document,
            upsert=True,
        )

    def get_knowledge_graph(
        self,
        video_id: str,
    ) -> dict | None:

        document = self.knowledge_graph.find_one({"video_id": video_id})

        if document is None:
            return None

        return document.get("result")

    def close(self) -> None:
        self.client.close()
