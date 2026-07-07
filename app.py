from storage.sqlite_storage import SQLiteStorage
from video_processor.services.formatter import transcript_to_timestamped
from video_processor.services.parser import extract_video_id
from video_processor.services.youtube_service import YoutubeTranscriptService
from video_processor.utils.file_utils import save_text


url = input("Enter a YouTube URL : ")

video_id = extract_video_id(url)

service = YoutubeTranscriptService()

transcript = service.fetch_transcript(video_id)

timed_text = transcript_to_timestamped(transcript)


print(type(transcript.video_id), transcript.video_id)
print(type(transcript.language), transcript.language)
print(type(transcript.language_code), transcript.language_code)
#print(type(transcript.segments), transcript.segments)


db = SQLiteStorage()

# Save a transcript
db.save(
    transcript.video_id,
    transcript.language,
    transcript.language_code,
    transcript.text
)

# Retrieve it
result = db.get(transcript.video_id)

if result:
    print(f"Language_Code: {result['language_code']}")
#print(result)

#save_text("output.txt", timed_text)

print("Done!")


