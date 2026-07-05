from video_processor.services.formatter import transcript_to_timestamped
from video_processor.services.parser import extract_video_id
from video_processor.services.youtube_service import YoutubeTranscriptService
from video_processor.utils.file_utils import save_text


url = input("Enter a YouTube URL : ")

video_id = extract_video_id(url)

service = YoutubeTranscriptService()

transcript = service.fetch_transcript(video_id)

text = transcript_to_timestamped(transcript)

save_text("output.txt", text)

print("Done!")


