from storage.services.transcript_service import TranscriptService
from video_processor.services.parser import extract_video_id


url = input("Enter a YouTube URL : ")

video_id = extract_video_id(url)

t_service = TranscriptService()

transcript = t_service.get(video_id)

print(transcript.text)

