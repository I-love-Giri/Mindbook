"""
For most RAG applications (chatbots over PDFs, transcripts, documentation), the sentence-aware token chunker is usually the better choice because it preserves natural language structure while still respecting token limits. The raw token approach is useful when you need strict control over chunk size.

"""

from typing import List, Dict
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
    ):
        self.semantic_splitter = SemanticSplitter()

        self.version = version

        self.max_words = max_words
        self.overlap_words = overlap_words

        self.soft_limit = int(max_words * soft_limit_ratio)

        self.pause_threshold = pause_threshold

        self.cleaner = TranscriptCleaner()

    def chunk(self, segments: List[Segment], video_id: str) -> List[Dict]:

        if self.version == self.VERSION_BASIC:

            units = self.prepare_segments(segments)

        elif self.version == self.VERSION_SOFT_LIMIT:

            units = self.merge_into_sentences(segments)

        elif self.version == self.VERSION_SEMANTIC:

            sentences = self.merge_into_sentences(segments)

            semantic_groups = self.semantic_splitter.split(sentences)

            units = [self.merge_group(group) for group in semantic_groups]

            units = self.merge_into_sentences(segments)

        else:
            raise ValueError(f"Unknown version {self.version}")

        return self.chunk_units(units, video_id)

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
