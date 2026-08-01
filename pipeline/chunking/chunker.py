'''
For most RAG applications (chatbots over PDFs, transcripts, documentation), the sentence-aware token chunker is usually the better choice because it preserves natural language structure while still respecting token limits. The raw token approach is useful when you need strict control over chunk size.

'''

from typing import List, Dict
from pipeline.cleaning.cleaner import TranscriptCleaner
from video_processor.models.transcript import Segment


class TranscriptChunker:

    VERSION_BASIC = 1
    VERSION_SOFT_LIMIT = 2
    VERSION_SEMANTIC = 3


    def __init__(
        self,
        version: int = VERSION_SEMANTIC,
        max_words: int = 300,
        overlap_words: int = 50,
        soft_limit_ratio: float = 0.75
    ):

        self.version = version

        self.max_words = max_words
        self.overlap_words = overlap_words

        self.soft_limit = int(
            max_words * soft_limit_ratio
        )

        self.cleaner = TranscriptCleaner()



    def chunk(
        self,
        segments: List[Segment],
        video_id: str
    ) -> List[Dict]:

        if self.version == self.VERSION_BASIC:

            return self._chunk(
                segments,
                video_id,
                use_soft_limit=False,
                use_boundaries=False,
                use_pause=False
            )


        elif self.version == self.VERSION_SOFT_LIMIT:

            return self._chunk(
                segments,
                video_id,
                use_soft_limit=True,
                use_boundaries=False,
                use_pause=False
            )


        elif self.version == self.VERSION_SEMANTIC:

            return self._chunk(
                segments,
                video_id,
                use_soft_limit=True,
                use_boundaries=True,
                use_pause=True
            )


        else:
            raise ValueError(
                f"Unknown chunking version: {self.version}"
            )



    def _chunk(
        self,
        segments: List[Segment],
        video_id: str,
        use_soft_limit: bool,
        use_boundaries: bool,
        use_pause: bool
    ) -> List[Dict]:
        
        last_boundary_index = None

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


            current_segments.append(
                segment_data
            )

            current_word_count += words


            should_split = False



            # ---------------------------
            # Version 1
            # max_words only
            # ---------------------------
            # Version 1
            if not use_soft_limit:

                if current_word_count >= self.max_words:
                    should_split = True


            # Version 2 / Version 3
            else:

                # Once we cross the soft limit...
                if current_word_count >= self.soft_limit:

                    if use_boundaries or use_pause:

                        previous_segment = (
                            current_segments[-2]
                            if len(current_segments) > 1
                            else None
                        )

                        boundary_found = (
                            use_boundaries
                            and
                            self.is_natural_boundary(cleaned_text)
                        )

                        pause_found = (
                            use_pause
                            and
                            previous_segment
                            and
                            self.has_pause(
                                previous_segment,
                                segment_data
                            )
                        )

                        # Remember the latest good split point
                        if boundary_found or pause_found:
                            last_boundary_index = (
                                len(current_segments) - 1
                            )

                    else:
                        # Version 2:
                        # split immediately after soft limit
                        should_split = True


                # Force split at max limit
                if current_word_count >= self.max_words:

                    if (
                        use_boundaries
                        and
                        last_boundary_index is not None
                    ):

                        # Split at the last sentence boundary
                        chunk_segments = (
                            current_segments[
                                :last_boundary_index + 1
                            ]
                        )

                        chunks.append(
                            self.create_chunk(
                                chunk_segments,
                                video_id,
                                len(chunks)
                            )
                        )

                        overlap = self.create_overlap(
                            chunk_segments
                        )

                        remaining = (
                            current_segments[
                                last_boundary_index + 1:
                            ]
                        )

                        current_segments = (
                            overlap + remaining
                        )

                        current_word_count = sum(
                            len(item["text"].split())
                            for item in current_segments
                        )

                        last_boundary_index = None

                        continue

                    else:
                        should_split = True


            if should_split:

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


                current_segments = overlap


                current_word_count = sum(
                    len(item["text"].split())
                    for item in current_segments
                )



        # Remaining chunk

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


            if (
                words + segment_words
                <= self.overlap_words
            ):

                overlap.insert(
                    0,
                    segment
                )

                words += segment_words

            else:
                break


        return overlap



    def is_natural_boundary(
        self,
        text: str
    ) -> bool:

        text = text.strip().lower()


        markers = [
            "now",
            "next",
            "moving on",
            "let's move on",
            "another thing",
            "finally",
            "in conclusion",
            "so",
            "the next",
        ]


        if any(
            text.startswith(marker)
            for marker in markers
        ):
            return True


        if text.endswith(
            (
                ".",
                "?",
                "!"
            )
        ):
            return True


        return False



    def has_pause(
        self,
        previous: Dict,
        current: Dict,
        threshold: float = 1.5
    ) -> bool:

        previous_end = (
            previous["start"]
            +
            previous["duration"]
        )


        gap = (
            current["start"]
            -
            previous_end
        )


        return gap >= threshold
