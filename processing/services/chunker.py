'''
For most RAG applications (chatbots over PDFs, transcripts, documentation), the sentence-aware token chunker is usually the better choice because it preserves natural language structure while still respecting token limits. The raw token approach is useful when you need strict control over chunk size.

'''

from typing import List, Dict
from processing.services.cleaner import TranscriptCleaner
class TranscriptChunker:

    def __init__(
        self,
        max_words: int = 500,
        overlap_words: int = 50
    ):
        self.max_words = max_words
        self.overlap_words = overlap_words
        self.cleaner = TranscriptCleaner()


    def chunk(
        self,
        segments: List[Dict],
        video_id: str
    ) -> List[Dict]:

        chunks = []

        current_segments = []
        current_word_count = 0


        for segment in segments:

            cleaned_text = self.cleaner.clean(
                segment.text
            )

            if not cleaned_text:
                continue


            segment_data = {
                "text": cleaned_text,
                "start": segment.start,
                "duration": segment.duration
            }



            words = len(
                cleaned_text.split()
            )


            if current_word_count + words <= self.max_words:

                current_segments.append(
                    segment_data
                )

                current_word_count += words


            else:

                if current_segments:

                    chunks.append(
                        self.create_chunk(
                            current_segments,
                            video_id,
                            len(chunks)
                        )
                    )


                overlap = self.create_overlap(
                    current_segments
                )


                current_segments = (
                    overlap +
                    [segment_data]
                )


                current_word_count = sum(
                    len(
                        item["text"].split()
                    )
                    for item in current_segments
                )


        if current_segments:

            chunks.append(
                self.create_chunk(
                    current_segments,
                    video_id,
                    len(chunks)
                )
            )


        return chunks



    def create_chunk(
        self,
        segments: List[Dict],
        video_id: str,
        chunk_id: int
    ) -> Dict:


        text = " ".join(
            segment["text"]
            for segment in segments
        )


        start = segments[0]["start"]


        last_segment = segments[-1]

        end = (
            last_segment["start"]
            +
            last_segment["duration"]
        )


        return {

            "chunk_id": chunk_id,

            "video_id": video_id,

            "text": text,

            "start": round(start, 2),

            "end": round(end, 2),

            "word_count": len(text.split())
        }



    def create_overlap(
        self,
        segments: List[Dict]
    ) -> List[Dict]:

        overlap = []

        words = 0


        for segment in reversed(segments):

            segment_words = len(
                segment["text"].split()
            )


            if words + segment_words <= self.overlap_words:

                overlap.insert(
                    0,
                    segment
                )

                words += segment_words

            else:
                break


        return overlap

