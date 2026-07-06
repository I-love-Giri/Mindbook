import sqlite3


class SQLiteStorage:

    def __init__(self):

        self.conn = sqlite3.connect("transcripts.db")

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            language TEXT,
            langauge_code TEXT,
            transcript TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

    def save(self, video_id, title, language, language_code, transcript):
        self.conn.execute(
            """
            INSERT OR REPLACE INTO transcripts
            (video_id, title, language, language_code, transcript)
            VALUES (?, ?, ?, ?, ?)
            """,
            (video_id, title, language, language_code, transcript),
        )

        self.conn.commit()

    def get(self, video_id):

        cursor = self.conn.execute(
            """
            SELECT video_id, title, language, transcript
            FROM transcripts
            WHERE video_id=?
            """,
            (video_id,),
        )

        row = cursor.fetchone()

        if row:
            return {
                "video_id": row[0],
                "title": row[1],
                "language": row[2],
                "language_code": row[3],
                "transcript": row[4],
            }

        return None

'''

if __name__ == "__main__":

    storage = SQLiteStorage()

    storage.save(
        "abc123",
        "[00:00:00] Hello\n[00:00:01] Welcome to the video."
    )

    transcript = storage.get("abc123")

    print(transcript)

Output :

'''
