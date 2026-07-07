import sqlite3

class SQLiteStorage:

    def __init__(self):
        self.conn = sqlite3.connect("transcripts.db")

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            video_id TEXT PRIMARY KEY,
            language TEXT,
            language_code TEXT,
            segments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

    def save(self, video_id, language, language_code, segments):
        self.conn.execute(
            """
            INSERT OR REPLACE INTO transcripts
            (video_id, language, language_code, segments)
            VALUES (?, ?, ?, ?)
            """,
            (video_id, language, language_code, segments),
        )
        self.conn.commit()

    def get(self, video_id):
        cursor = self.conn.execute(
            """
            SELECT video_id, language, language_code, segments
            FROM transcripts
            WHERE video_id = ?
            """,
            (video_id,),
        )

        row = cursor.fetchone()

        if row:
            return {
                "video_id": row[0],
                "language": row[1],
                "language_code": row[2],
                "segments": row[3],
            }

        return None
    
    def close(self) -> None: 
        self.conn.close()

'''

if __name__ == "__main__":

    storage = SQLiteStorage()

    storage.save(
        "abc123",
        "[00:00:00] Hello\n[00:00:01] Welcome to the video."
    )

    segments = storage.get("abc123")

    print(segments)

Output :

-----------------

storage = SQLiteStorage()

storage.save(
    video_id=segments.video_id,
    title=title,
    language=segments.language,
    language_code=segments.language_code,
    segments=segments.text,
)

data = storage.get(segments.video_id)

if data:
    print(data["title"])
    print(data["segments"])

storage.close()

'''
