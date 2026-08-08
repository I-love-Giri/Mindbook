"""
For most RAG applications (chatbots over PDFs, transcripts, documentation), the sentence-aware token chunker is usually the better choice because it preserves natural language structure while still respecting token limits. The raw token approach is useful when you need strict control over chunk size.

"""

from typing import List, Dict, Optional
import re

from pipeline.cleaning.cleaner import TranscriptCleaner
from video_processor.models.transcript import Segment
from pipeline.chunking.semantic_splitter import SemanticSplitter


class TranscriptChunker:

    VERSION_BASIC = 1
    VERSION_SOFT_LIMIT = 2
    VERSION_SEMANTIC = 3

    def __init__(
        self,
        version: int = VERSION_SEMANTIC,
        max_words: int = 300,
        overlap_words: int = 50,
        soft_limit_ratio: float = 0.75,
        pause_threshold: float = 2.0,
        min_chapter_duration: float = 60.0,
    ):
        self.semantic_splitter = SemanticSplitter()

        self.version = version

        self.max_words = max_words
        self.overlap_words = overlap_words

        self.soft_limit = int(max_words * soft_limit_ratio)

        self.pause_threshold = pause_threshold

        self.min_chapter_duration = min_chapter_duration

        self.cleaner = TranscriptCleaner()

    def chunk(
        self,
        segments: List[Segment],
        video_id: str,
        chapters: Optional[List[Dict]] = None,
        duration: Optional[float] = None,
    ) -> List[Dict]:
        """
        Chunk a transcript into dicts with a "text" key, and always a
        "title" key.

        If `chapters` is given (e.g. real YouTube chapter markers, each
        a dict with "title" and "start_time"), chunking is scoped to
        each chapter's segments so section boundaries line up with the
        video's own structure and every chunk carries the chapter's
        real title. Chapters shorter than `min_chapter_duration` are
        merged into the following chapter first, so content-free
        intros/outros don't waste an LLM call on their own.

        If a chapter is long enough to still exceed max_words, it is
        split further using the normal word-limit/overlap logic below,
        and the resulting parts are titled "<Chapter Title> (Part N)".

        If `chapters` is not given (or empty), falls back to the
        original whole-transcript chunking behavior with no title key
        set — callers are expected to derive a fallback title
        themselves in that case (see Summarizer._chunk_title).
        """

        if chapters:
            return self._chunk_with_chapters(segments, video_id, chapters, duration)

        units = self._build_units(segments)

        return self.chunk_units(units, video_id)

    # --------------------------------------------------
    # Chapter-aware chunking
    # --------------------------------------------------

    def _merge_short_chapters(
        self,
        chapters: List[Dict],
        duration: float,
    ) -> List[tuple]:
        """
        Returns a list of (start, end, title) windows, merging any
        chapter shorter than self.min_chapter_duration forward into
        the following chapter(s) until the merged window is long
        enough (or there's nothing left to merge into).

        The merged window's title is taken from whichever absorbed
        sub-chapter had the longest individual span, not simply the
        first one — a short "Quick aside" merged into a much longer
        "How Decorators Work" chapter should end up titled after the
        substantial content, not the filler that triggered the merge.
        """

        boundaries = [
            (float(c["start_time"]), c.get("title", "Untitled")) for c in chapters
        ]
        boundaries.append((duration, None))

        n = len(boundaries)
        windows = []
        i = 0

        while i < n - 1:

            window_start = boundaries[i][0]
            end = boundaries[i + 1][0]

            candidates = [(end - window_start, boundaries[i][1])]

            while (end - window_start) < self.min_chapter_duration and i + 2 < n:
                i += 1
                end = boundaries[i + 1][0]
                span = end - boundaries[i][0]
                candidates.append((span, boundaries[i][1]))

            best_title = max(candidates, key=lambda c: c[0])[1]
            windows.append((window_start, end, best_title))
            i += 1

        return windows

    def _build_units(self, segments: List[Segment]) -> List[Dict]:
        """
        Runs the configured version's unit-building logic (sentence
        merging, semantic grouping, etc) over a set of segments. Shared
        by both the chapter-scoped path and the whole-transcript path
        so chapters get the exact same quality of sentence/semantic
        boundaries as before, just scoped to a smaller window.
        """

        if self.version == self.VERSION_BASIC:
            return self.prepare_segments(segments)

        if self.version == self.VERSION_SOFT_LIMIT:
            return self.merge_into_sentences(segments)

        if self.version == self.VERSION_SEMANTIC:
            sentences = self.merge_into_sentences(segments)
            semantic_groups = self.semantic_splitter.split(sentences)
            return [self.merge_group(group) for group in semantic_groups]

        raise ValueError(f"Unknown version {self.version}")

    def _chunk_with_chapters(
        self,
        segments: List[Segment],
        video_id: str,
        chapters: List[Dict],
        duration: Optional[float],
    ) -> List[Dict]:

        if duration is None:
            duration = max(
                (s.start + s.duration for s in segments),
                default=0.0,
            )

        windows = self._merge_short_chapters(chapters, duration)

        all_chunks: List[Dict] = []
        chunk_id = 0

        for start, end, title in windows:

            chapter_segments = [s for s in segments if start <= s.start < end]

            if not chapter_segments:
                continue

            units = self._build_units(chapter_segments)

            chapter_chunks = self.chunk_units(units, video_id)

            multi_part = len(chapter_chunks) > 1

            for part_index, ch in enumerate(chapter_chunks):
                ch["chunk_id"] = chunk_id
                ch["title"] = (
                    f"{title} (Part {part_index + 1})" if multi_part else title
                )
                all_chunks.append(ch)
                chunk_id += 1

        return all_chunks

    # --------------------------------------------------
    # Clean Whisper output
    # --------------------------------------------------

    def prepare_segments(self, segments: List[Segment]) -> List[Dict]:

        result = []

        for segment in segments:

            text = self.cleaner.clean(segment.text)

            if not text:
                continue

            result.append(
                {
                    "text": text,
                    "start": segment.start,
                    "duration": segment.duration,
                    "end": (segment.start + segment.duration),
                    "words": len(text.split()),
                }
            )

        return result

    # --------------------------------------------------
    # Convert Whisper segments into sentences
    # --------------------------------------------------

    def merge_into_sentences(self, segments: List[Segment]) -> List[Dict]:

        cleaned = self.prepare_segments(segments)

        sentences = []

        current = []

        start = None

        previous_end = None

        for segment in cleaned:

            if start is None:
                start = segment["start"]

            gap = 0

            if previous_end:

                gap = segment["start"] - previous_end

            current.append(segment)

            text = " ".join(x["text"] for x in current)

            boundary = (
                self.ends_sentence(text)
                or gap > self.pause_threshold
                or self.looks_like_topic_shift(current)
            )

            if boundary:

                sentences.append(self.create_sentence(current, start))

                current = []
                start = None

            previous_end = segment["end"]

        if current:

            sentences.append(self.create_sentence(current, start))

        return sentences

    def merge_group(self, group):

        text = " ".join(x["text"] for x in group)

        end = group[-1]["start"] + group[-1]["duration"]

        return {
            "text": text,
            "start": group[0]["start"],
            "duration": group[-1]["start"] + group[-1]["duration"] - group[0]["start"],
            "end": end,
            "words": len(text.split()),
        }

    def create_sentence(self, units, start):

        text = " ".join(x["text"] for x in units)

        return {
            "text": text,
            "start": start,
            "duration": units[-1]["end"] - start,
            "end": units[-1]["end"],
            "words": len(text.split()),
        }

    def ends_sentence(self, text: str) -> bool:

        return bool(re.search(r"[.!?][\"']?$", text.strip()))

    def looks_like_topic_shift(self, units) -> bool:

        if len(units) < 2:
            return False

        text = units[-1]["text"].lower()

        starters = [
            "now",
            "next",
            "another",
            "finally",
            "however",
            "in conclusion",
            "let's move",
            "moving on",
        ]

        return any(text.startswith(x) for x in starters)

    # --------------------------------------------------
    # Chunk creation
    # --------------------------------------------------

    def chunk_units(self, units: List[Dict], video_id: str) -> List[Dict]:

        chunks = []

        current = []

        words = 0

        for unit in units:

            if unit["words"] > self.max_words:

                if current:

                    chunks.append(self.create_chunk(current, video_id, len(chunks)))

                    current = []

                    words = 0

                chunks.extend(self.split_long_unit(unit, video_id, len(chunks)))

                continue

            current.append(unit)

            words += unit["words"]

            split = False

            if self.version == self.VERSION_BASIC:

                split = words >= self.max_words

            elif self.version in (self.VERSION_SOFT_LIMIT, self.VERSION_SEMANTIC):

                # Semantic groups are already natural boundaries.
                # Soft limit decides when to emit a chunk.
                split = words >= self.soft_limit

            # Hard safety limit
            if words >= self.max_words:
                split = True

            if split:

                chunks.append(self.create_chunk(current, video_id, len(chunks)))

                current = self.create_overlap(current)

                words = sum(x["words"] for x in current)

        if current:

            chunks.append(self.create_chunk(current, video_id, len(chunks)))

        return chunks

    # --------------------------------------------------
    # Split huge sentences safely
    # --------------------------------------------------

    def split_long_unit(self, unit: Dict, video_id: str, chunk_id: int) -> List[Dict]:

        words = unit["text"].split()

        chunks = []

        step = self.max_words - self.overlap_words

        for i in range(0, len(words), step):

            part = words[i : i + self.max_words]

            text = " ".join(part)

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "video_id": video_id,
                    "text": text,
                    "start": round(unit["start"], 2),
                    "end": round(unit.get("end", unit["start"] + unit["duration"]), 2),
                    "word_count": len(part),
                }
            )

            chunk_id += 1

        return chunks

    # --------------------------------------------------
    # Overlap
    # --------------------------------------------------

    def create_overlap(self, units: List[Dict]) -> List[Dict]:

        result = []

        count = 0

        for unit in reversed(units):

            if count + unit["words"] <= self.overlap_words:

                result.insert(0, unit)

                count += unit["words"]

            else:

                break

        return result

    # --------------------------------------------------
    # Final output
    # --------------------------------------------------

    def create_chunk(self, units: List[Dict], video_id: str, chunk_id: int) -> Dict:

        text = " ".join(x["text"] for x in units)

        return {
            "chunk_id": chunk_id,
            "video_id": video_id,
            "text": text,
            "start": round(units[0]["start"], 2),
            "end": round(units[-1]["end"], 2),
            "word_count": len(text.split()),
        }
