from youtube_transcript_api import IpBlocked, YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound
from video_processor.models.transcript import Segment, Transcript
import json
class YoutubeTranscriptService:

    '''
    def __init__(self):
        self.api = YouTubeTranscriptApi
    '''

    def fetch_transcript(self, video_id: str):

        api = YouTubeTranscriptApi()

        try:
            transcript_list = api.list(video_id)
        except IpBlocked:
            raise RuntimeError( "YouTube blocked transcript requests from your current IP." )

        # print(f"transcript_list: {transcript_list}")

        languages = [t.language_code for t in transcript_list]

        try:
            transcript = transcript_list.find_manually_created_transcript(
                languages
            )
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(
                languages
            )

        fetched = transcript.fetch()

        '''
        It's just a shorter way of writing:

        segments = []

        for seg in fetched:
            segments.append({
                 "text": seg.text,
                 "start": seg.start,
                 "duration": seg.duration,
            })
        '''

        segments = [Segment( text = snippet.text,
                            start = snippet.start,
                             duration = snippet.duration )
                    
                   for snippet in fetched ]

        return Transcript(language_code = transcript.language_code,
                          video_id = transcript.video_id,
                          language = transcript.language,
                          segments = segments
                          )

    
'''

User gives video_id
        │
        ▼
Connect to YouTube Transcript API
        │
        ▼
List all available transcripts
        │
        ▼
Try manual transcript
        │
   ┌────┴─────┐
   │          │
Found?      Not Found
   │          │
   ▼          ▼
Use it   Try generated transcript
   │          │
   └────┬─────┘
        ▼
Fetch transcript data
        ▼
Convert individual segments or snippet of fetched transcript into:
 {
   text,
   start,
   duration
 }
        │
        ▼
Return:
(language, segments)



------------------------------------------------------------------------


how transcripts list appear : 

transcript_list: For this video (9S-uO10nXcE) transcripts are available in the following languages:

(MANUALLY CREATED)
None

(GENERATED)
 - en ("English (auto-generated)")[TRANSLATABLE]

(TRANSLATION LANGUAGES)
 - ar ("Arabic")
 - zh-Hant ("Chinese (Traditional)")
 - nl ("Dutch")
 - fr ("French")
 - de ("German")
 - hi ("Hindi")
 - id ("Indonesian")
 - it ("Italian")
 - ja ("Japanese")
 - ko ("Korean")
 - pt ("Portuguese")
 - ru ("Russian")
 - es ("Spanish")
 - th ("Thai")
 - uk ("Ukrainian")
 - vi ("Vietnamese")

Initial fetched Data : 

FetchedTranscriptSnippet(text='anyway. Time is never on your side. So', start=777.44, duration=5.8), FetchedTranscriptSnippet(text='use it.', start=780.0, duration=3.24), FetchedTranscriptSnippet(text='Hey,', start=813.839, duration=3.0), FetchedTranscriptSnippet(text='hey, hey.', start=822.16, duration=3.0)], video_id='9S-uO10nXcE', language='English (auto-generated)', language_code='en', is_generated=True

fetch() returns FetchedTranscriptSnippet objects (with attributes like .text, .start, .duration)

with open(f"{video_id}_transcript.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

'''
