import json
import sqlite3

from video_processor.models.transcript import Segment, Transcript

class SQLiteStorage:
    def __init__(self, db_path: str = "transcripts.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transcripts (
                video_id TEXT PRIMARY KEY,
                language TEXT,
                language_code TEXT,
                segments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    def save(self, transcript: Transcript) -> None:
        """Persist a full Transcript, including per-segment timing, as JSON."""

        segments_json = json.dumps(
            [
                {
                    "text": seg.text,
                    "start": seg.start,
                    "duration": seg.duration,
                }
                for seg in transcript.segments
            ]
        )

        self.conn.execute(
            """
            INSERT OR REPLACE INTO transcripts
            (video_id, language, language_code, segments)
            VALUES (?, ?, ?, ?)
            """,
            (
                transcript.video_id,
                transcript.language,
                transcript.language_code,
                segments_json,
            ),
        )
        self.conn.commit()

    def get(self, video_id: str):
        """Return a fully reconstructed Transcript object, or None."""

        cursor = self.conn.execute(
            """
            SELECT video_id, language, language_code, segments
            FROM transcripts
            WHERE video_id = ?
            """,
            (video_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        video_id, language, language_code, segments_json = row

        raw_segments = json.loads(segments_json)
        
        segments = [
            Segment(
                text=s["text"],
                start=s["start"],
                duration=s["duration"],
            )
            for s in raw_segments
        ]

        return Transcript(
            video_id=video_id,
            language=language,
            language_code=language_code,
            segments=segments,
        )

    def close(self) -> None:
        self.conn.close()
