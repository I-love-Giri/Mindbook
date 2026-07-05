import sys
from video_processor.models import Transcript
from video_processor.services.parser import extract_video_id
from video_processor.services.youtube_service import fetch_transcript

if __name__ == "__main__":
    id = extract_video_id(sys.argv[1])
    print(id)

    transcript = Transcript()
    transcript.language_code , transcript.text = fetch_transcript(id)