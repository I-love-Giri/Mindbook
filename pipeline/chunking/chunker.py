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
            if not use_soft_limit:

                should_split = (
                    current_word_count >= self.max_words
                )


            # ---------------------------
            # Version 2 / 3
            # soft limit
            # ---------------------------
            else:

                if current_word_count >= self.soft_limit:

                    should_split = True


                    # ---------------------------
                    # Version 3 additions
                    # ---------------------------
                    if (
                        use_boundaries
                        or use_pause
                    ):

                        previous_segment = (
                            current_segments[-2]
                            if len(current_segments) > 1
                            else None
                        )


                        boundary_found = (
                            use_boundaries
                            and
                            self.is_natural_boundary(
                                cleaned_text
                            )
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


                        should_split = (
                            boundary_found
                            or
                            pause_found
                        )



            # Always force split at max limit
            if current_word_count >= self.max_words:

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
